#!/usr/bin/env python3
"""Scan this repository for the personal data a recipe collection leaks.

A receipt leaks a household through numbers. A recipe collection leaks it through
*people*: whose recipe this is, who was at the dinner, whose allergy the
substitution is for, which grandmother the pie belongs to. None of that looks like
a pattern, so this scanner has two tiers and the second one matters more:

1. **Rules** for the things that do look like patterns — email addresses, phone
   numbers, street addresses, coordinates, home-directory paths, and URLs that
   point at private places rather than published ones.
2. **A literal denylist** of the names and contact details that must never appear,
   kept out of the repository and matched through salted digests so that CI can
   run it too. See `tools/denylist.py` and SECURITY.md.

The `private/` directory is skipped entirely. It is gitignored, refused by a
commit hook, and is where the recipes this household does not publish live.

False positives are suppressed one line at a time, with a reason:

    A dish from Cafe Verano on Anchor Parade.  -- scan: allow invented place

Usage:
    python3 -m tools.scan_personal              the whole tree
    python3 -m tools.scan_personal PATH ...     specific paths (how pre-commit calls it)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    from tools.denylist import EMPTY as EMPTY_DENYLIST
    from tools.denylist import Denylist, load_denylist
except ImportError:  # invoked as a path rather than as `python -m tools.scan_personal`
    sys.path.insert(0, str(REPO_ROOT))
    from tools.denylist import EMPTY as EMPTY_DENYLIST
    from tools.denylist import Denylist, load_denylist

SUPPRESSION = re.compile(r"scan:\s*allow\b(?P<reason>.*)")

SKIP_DIR_PARTS = {".git", "private", "__pycache__", ".venv", "node_modules"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".heic", ".webp", ".gif", ".pdf", ".zip"}
# Files that describe the rules necessarily contain examples of what they forbid.
SELF_DOCUMENTING = {
    "tools/scan_personal.py",
    "tools/denylist.py",
    "SECURITY.md",
    "CONTRIBUTING.md",
}

# The one place the copyright holder's own name is required rather than leaked:
# an MIT licence that does not name its holder is not an MIT licence, and the
# name is already public in every commit's authorship. Only the names tier stands
# down here — the rules tier still runs, so an address or a phone number added to
# this file is still caught.
NAME_EXPECTED = {"LICENSE"}


@dataclass(frozen=True)
class Finding:
    origin: str
    line_no: int
    rule: str
    matched: str
    hint: str

    def render(self) -> str:
        return f"{self.origin}:{self.line_no}: [{self.rule}] {mask(self.matched)}\n    {self.hint}"


def mask(text: str) -> str:
    """Show enough to locate the hit, not enough to leak it."""
    text = text.strip()
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:2]}{'*' * (len(text) - 4)}{text[-2:]}"


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    hint: str


RULES: tuple[Rule, ...] = (
    Rule(
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.(?:com|org|net)\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "An email address. Use example.com if you need one at all.",
    ),
    Rule(
        "PHONE",
        # 555 is the reserved *exchange* — the middle three digits, not the area
        # code. Putting the exception on the area code flags every fabricated
        # number and teaches people to suppress the rule.
        re.compile(r"(?<!\d)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?(?!555)\d{3}[-. ]?\d{4}(?!\d)"),
        "A phone number. Use the 555 exchange if you need one at all.",
    ),
    Rule(
        "STREET",
        re.compile(
            r"\b\d{1,6}\s+(?:[A-Z][A-Za-z.'-]*\s+){0,4}"
            r"(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Ln|Lane|Dr|Drive|Ct|Court|Way|Pl|"
            r"Place|Ter|Terrace|Cir|Circle|Hwy|Highway|Pkwy|Parkway|Trl|Trail|Loop|Row|Walk|"
            r"Mews|Crescent|Alley|Grove)\b\.?"
        ),
        "A street address. Invent one, and suppress the line saying so.",
    ),
    Rule(
        "COORDS",
        re.compile(r"(?<![\d.])-?\d{1,3}\.\d{3,}\s*,\s*-?\d{1,3}\.\d{3,}(?![\d.])"),
        "A coordinate pair identifies a household as surely as an address.",
    ),
    Rule(
        "LOCAL_PATH",
        re.compile(r"(?:/Users|/home)/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*"),
        "An absolute path under a home directory leaks the account name. "
        "Use a relative path or $HOME.",
    ),
    Rule(
        "PRIVATE_URL",
        re.compile(
            r"https?://(?:[A-Za-z0-9.-]*\.)?"
            r"(?:photos\.google|drive\.google|docs\.google|icloud|dropbox|onedrive|notion\.so)"
            r"[^\s)\]]*"
        ),
        "A link into private storage. It may be unlisted, but it is not private "
        "once it is in a public repository.",
    ),
)


def suppressed(line: str, preceding: str = "") -> bool:
    """A marker with a written reason, on this line or the one above it."""
    for candidate in (line, preceding):
        m = SUPPRESSION.search(candidate)
        if m and m.group("reason").strip():
            return True
    return False


def scan_lines(lines: list[str], origin: str, denylist: Denylist) -> list[Finding]:
    found: list[Finding] = []
    apply_rules = origin not in SELF_DOCUMENTING
    apply_names = origin not in NAME_EXPECTED
    for idx, line in enumerate(lines, start=1):
        if suppressed(line, lines[idx - 2] if idx > 1 else ""):
            continue
        if apply_names:
            for matched in denylist.find(line.lower()):
                found.append(
                    Finding(origin, idx, "DENYLIST", matched, "Literal string from the denylist.")
                )
        if not apply_rules:
            continue
        for rule in RULES:
            for m in rule.pattern.finditer(line):
                found.append(Finding(origin, idx, rule.name, m.group(0), rule.hint))
    return found


def is_scannable(path: Path) -> bool:
    if any(part in SKIP_DIR_PARTS for part in path.parts):
        return False
    return path.suffix.lower() not in SKIP_SUFFIXES


def tracked_and_untracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return [p for p in out.splitlines() if p]


def scan_paths(paths: list[str], denylist: Denylist) -> list[Finding]:
    findings: list[Finding] = []
    for rel in paths:
        path = REPO_ROOT / rel
        if not path.is_file() or not is_scannable(Path(rel)):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        findings += scan_lines(text.splitlines(), rel, denylist)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)

    denylist = load_denylist() or EMPTY_DENYLIST
    paths = args.paths or tracked_and_untracked()
    findings = scan_paths(paths, denylist)

    if not findings:
        note = (
            f"  (denylist: {denylist.size} entries via {denylist.source})"
            if denylist
            else "  (NO DENYLIST — the names tier is not running; see SECURITY.md)"
        )
        print(f"scan_personal: clean — {len(paths)} path(s){note}")
        # A denylist holding nothing but the canary passes every scan and proves
        # nothing. In a public repository of real recipes that is the gap that
        # matters, so say so rather than letting a green check imply otherwise.
        if 0 < denylist.size <= 1:
            print(
                "scan_personal: WARNING — the names tier holds only the canary, "
                "so no person's name is being checked for.\n"
                "  Add the household's names, and those of anyone whose recipes "
                "are here, to tools/denylist.txt\n"
                "  (it is gitignored) and run `make denylist`. See SECURITY.md.",
                file=sys.stderr,
            )
        return 0

    print(f"scan_personal: {len(findings)} finding(s)\n", file=sys.stderr)
    for f in findings:
        print(f.render(), file=sys.stderr)
    print(
        "\nMatches are masked above. If a finding is genuinely benign, add"
        "\n  -- scan: allow <reason>"
        "\non the offending line or the line directly above it.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
