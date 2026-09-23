#!/usr/bin/env python3
"""Check that every relative link in the Markdown actually goes somewhere.

The documents here cross-reference each other constantly — the README sends you
to SECURITY.md and CONTRIBUTING.md, both of those send you back, and all three
point at files in `tools/`. Renaming a file breaks those links silently: GitHub
renders a dead relative link as ordinary blue text and nothing complains. On a
public repository that is a reader following a link about not publishing other
people's names and landing on a 404.

A Markdown linter will not catch this; it checks style, not destinations. Link
checkers that do exist are aimed at the network, which is the half this
repository cannot verify and does not need to: an outside URL rotting is not
something a commit hook should have an opinion about, and reaching out on every
commit would be both slow and a privacy leak in a repository whose whole point is
not talking to anyone.

So this checks only what is knowable offline:

  * a relative path resolves to a file that exists and is tracked;
  * a `#fragment` matches a heading in the file it points at, using GitHub's
    slug rules, so "See [the denylist](SECURITY.md#the-names-tier)" fails when
    that heading is renamed;
  * a link into `private/` is refused outright — that directory is gitignored,
    so the link is dead for every reader but its author.

External links (http, https, mailto) are listed as skipped and never fetched.

    python3 -m tools.check_links              every tracked Markdown file
    python3 -m tools.check_links PATH ...     specific files (how pre-commit calls it)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parent.parent

# Inline links and images: [text](target "optional title"), ![alt](target).
INLINE_LINK = re.compile(r"!?\[(?:[^\]\\]|\\.)*\]\(\s*<?([^)>\s]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
# Reference definitions: [label]: target "optional title"
REFERENCE_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?([^>\s]+)>?")
# Fenced code blocks, whose contents are examples rather than links.
FENCE = re.compile(r"^\s*(```|~~~)")

ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")

EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:", "ftp://")

# Characters GitHub strips when it turns a heading into an anchor. Letters,
# digits, spaces and hyphens survive; spaces become hyphens.
SLUG_STRIP = re.compile(r"[^\w\- ]", re.UNICODE)


@dataclass(frozen=True)
class Problem:
    path: str
    line: int
    target: str
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.target}\n    {self.message}"


def slugify(heading: str) -> str:
    """GitHub's anchor rules: strip formatting, lowercase, spaces to hyphens."""
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\*\*([^*]*)\*\*|\*([^*]*)\*|__([^_]*)__|_([^_]*)_", r"\1\2\3\4", text)
    text = INLINE_LINK.sub(lambda m: "", text)
    text = re.sub(r"[\[\]]", "", text)
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = SLUG_STRIP.sub("", text)
    return text.replace(" ", "-")


def headings_of(path: Path) -> set[str]:
    """Every anchor a Markdown file offers, with GitHub's duplicate suffixes."""
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    in_fence = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = ATX_HEADING.match(line)
        if not m:
            continue
        slug = slugify(m.group(2))
        if not slug:
            continue
        n = seen.get(slug, 0)
        seen[slug] = n + 1
        anchors.add(slug if n == 0 else f"{slug}-{n}")
        anchors.add(slug)
    return anchors


def targets_of(path: Path) -> list[tuple[int, str]]:
    """Every link target in a file, with its line number, skipping code blocks."""
    found: list[tuple[int, str]] = []
    in_fence = False
    for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        ref = REFERENCE_DEF.match(line)
        if ref:
            found.append((n, ref.group(1)))
            continue
        for m in INLINE_LINK.finditer(line):
            found.append((n, m.group(1)))
    return found


def tracked_markdown() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    ).stdout
    return [p for p in out.splitlines() if p]


def check_file(rel: str, anchors_cache: dict[Path, set[str]]) -> tuple[list[Problem], int]:
    path = REPO_ROOT / rel
    problems: list[Problem] = []
    skipped = 0
    for line_no, raw in targets_of(path):
        target = unquote(raw.strip())
        if target.startswith(EXTERNAL_SCHEMES):
            skipped += 1
            continue
        if target.startswith("#"):
            dest, fragment = path, target[1:]
        else:
            dest_str, _, fragment = target.partition("#")
            if not dest_str:
                continue
            dest = (path.parent / dest_str).resolve()
            if not str(dest).startswith(str(REPO_ROOT)):
                problems.append(
                    Problem(rel, line_no, target, "points outside the repository")
                )
                continue
            try:
                inside = dest.relative_to(REPO_ROOT)
            except ValueError:  # pragma: no cover - guarded above
                continue
            if inside.parts and inside.parts[0] == "private":
                problems.append(
                    Problem(
                        rel,
                        line_no,
                        target,
                        "points into private/, which is gitignored. The link is dead "
                        "for every reader but you.",
                    )
                )
                continue
            if not dest.exists():
                problems.append(Problem(rel, line_no, target, "no such file"))
                continue
        if not fragment:
            continue
        if dest.suffix.lower() != ".md":
            continue
        if dest not in anchors_cache:
            anchors_cache[dest] = headings_of(dest)
        if slugify(fragment) not in anchors_cache[dest]:
            where = "this file" if dest == path else dest.name
            problems.append(
                Problem(rel, line_no, target, f"no heading in {where} makes that anchor")
            )
    return problems, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)

    paths = [p for p in (args.paths or tracked_markdown()) if p.endswith(".md")]
    paths = [p for p in paths if (REPO_ROOT / p).is_file()]
    if not paths:
        print("check_links: no Markdown files to check")
        return 0

    anchors_cache: dict[Path, set[str]] = {}
    problems: list[Problem] = []
    skipped = 0
    for rel in paths:
        found, n = check_file(rel, anchors_cache)
        problems += found
        skipped += n

    if not problems:
        print(f"check_links: {len(paths)} file(s) OK ({skipped} external link(s) not fetched)")
        return 0

    print(f"check_links: {len(problems)} broken link(s)\n", file=sys.stderr)
    for p in problems:
        print(p.render(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
