#!/usr/bin/env python3
"""Validate every `.cook` file: front matter, Cooklang syntax, and attribution.

Kitchen ERP indexes this repository by scanning for `*.cook`, parsing each one,
and resolving its ingredient lines against a catalog. A file that does not parse
does not silently disappear — it is marked and the last good index is kept — but
it also does not cost anything, which is the whole point. Catching a malformed
recipe here is better than discovering it in the application.

The `source` field is required on every recipe, and that is a licensing control
rather than a tidiness one. An ingredient list and a bare method are not
copyrightable in the US, but the *expression* of a recipe is: headnotes,
descriptive prose, the particular wording of a step. This repository is public
and MIT-licensed, so every file has to say where it came from, and anything
adapted from a published source has to be written in the contributor's own words
with the original credited. See CONTRIBUTING.md.

No third-party dependency on purpose: a recipe repository that needs a virtualenv
to check a recipe is a recipe repository people stop checking. The front-matter
parser therefore accepts a documented subset of YAML — scalars, inline lists, and
folded or literal block scalars — which is all these files use.

    python3 -m tools.check_recipes              every recipe
    python3 -m tools.check_recipes PATH ...     specific files (how pre-commit calls it)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RECIPES_DIR = REPO_ROOT / "recipes"

REQUIRED = ("title", "source")
KNOWN_KEYS = {
    "title", "source", "servings", "tags", "notes", "course", "time", "author",
}

# Phrases that mean "this one is ours". Anything else in `source` is read as an
# attribution to someone else, and has to name them.
ORIGINAL = frozenset(
    {
        "invented for this repository",
        "family recipe",
        "our own",
        "my own",
        "original",
    }
)

# Values that look like an attribution but name nobody.
EMPTY_ATTRIBUTION = frozenset({"adapted", "family", "unknown", "n/a", "-", "none"})

FRONT_MATTER_FENCE = "---"

# Cooklang tokens. A name may be multi-word only when braces follow it.
INGREDIENT = re.compile(r"@(?P<name>[^@#~{}]*?)\{(?P<body>[^{}]*)\}|@(?P<bare>[\w'-]+)")
COOKWARE = re.compile(r"#(?P<name>[^@#~{}]*?)\{(?P<body>[^{}]*)\}|#(?P<bare>[\w'-]+)")
TIMER = re.compile(r"~(?P<name>[^@#~{}]*?)\{(?P<body>[^{}]*)\}")
QUANTITY = re.compile(r"^\s*(?P<amount>[^%]*?)\s*(?:%\s*(?P<unit>.+?)\s*)?$")


@dataclass
class Problem:
    path: str
    line: int
    message: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def split_front_matter(text: str, path: str) -> tuple[list[str], int, list[Problem]]:
    """Return (front matter lines, first body line number, problems)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONT_MATTER_FENCE:
        return [], 1, [Problem(path, 1, "no front matter; the file must start with ---")]
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONT_MATTER_FENCE:
            return lines[1:i], i + 2, []
    return [], 1, [Problem(path, 1, "front matter is never closed with ---")]


def parse_front_matter(lines: list[str], path: str, offset: int = 2) -> tuple[dict, list[Problem]]:
    """A documented subset of YAML: scalars, inline lists, folded/literal blocks."""
    data: dict[str, object] = {}
    problems: list[Problem] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        lineno = offset + i
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        if raw[:1].isspace():
            problems.append(Problem(path, lineno, "unexpected indentation in front matter"))
            i += 1
            continue
        key, sep, value = raw.partition(":")
        if not sep:
            problems.append(Problem(path, lineno, f"not a `key: value` line: {raw.strip()!r}"))
            i += 1
            continue
        key = key.strip()
        value = value.strip()
        if key in data:
            problems.append(Problem(path, lineno, f"duplicate key {key!r}"))
        if value in (">-", ">", "|", "|-"):
            block: list[str] = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i][:1].isspace()):
                block.append(lines[i].strip())
                i += 1
            joiner = "\n" if value.startswith("|") else " "
            data[key] = joiner.join(b for b in block if b)
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            items = [v.strip().strip("'\"") for v in inner.split(",")] if inner else []
            if any(not v for v in items):
                problems.append(Problem(path, lineno, f"empty item in list {key!r}"))
            data[key] = [v for v in items if v]
        else:
            data[key] = value.strip("'\"")
        i += 1
    return data, problems


def check_front_matter(data: dict, path: str) -> list[Problem]:
    problems: list[Problem] = []
    for key in REQUIRED:
        if not str(data.get(key, "")).strip():
            problems.append(Problem(path, 1, f"front matter is missing {key!r}"))

    source = str(data.get("source", "")).strip()
    if source and source.lower() not in ORIGINAL:
        # An attribution has to name something. "adapted" on its own does not
        # tell a reader whose words they are reading.
        if len(source) < 8 or source.lower() in EMPTY_ATTRIBUTION:
            problems.append(
                Problem(
                    path,
                    1,
                    f"source {source!r} names nothing. Say it is yours "
                    f"({', '.join(sorted(ORIGINAL))}), or credit the original "
                    "(title, author, where it was published). See CONTRIBUTING.md.",
                )
            )

    if "servings" in data:
        try:
            if int(str(data["servings"])) <= 0:
                raise ValueError
        except ValueError:
            problems.append(
                Problem(path, 1, f"servings must be a positive whole number, not {data['servings']!r}")
            )

    if "tags" in data and not isinstance(data["tags"], list):
        problems.append(Problem(path, 1, "tags must be an inline list, e.g. [quick, vegetarian]"))

    for key in data:
        if key not in KNOWN_KEYS:
            problems.append(
                Problem(path, 1, f"unknown front-matter key {key!r}; add it to KNOWN_KEYS if intended")
            )
    return problems


def check_body(body: str, path: str, offset: int) -> list[Problem]:
    problems: list[Problem] = []
    for n, line in enumerate(body.splitlines(), start=offset):
        if line.count("{") != line.count("}"):
            problems.append(Problem(path, n, "unbalanced braces"))
            continue
        if line.lstrip().startswith(">>"):
            problems.append(
                Problem(path, n, "`>>` metadata is not used here; put it in the front matter")
            )
        for pattern, kind in ((INGREDIENT, "ingredient"), (COOKWARE, "cookware"), (TIMER, "timer")):
            for m in pattern.finditer(line):
                if m.groupdict().get("bare"):
                    continue
                name = (m.group("name") or "").strip()
                body_text = m.group("body")
                if kind != "timer" and not name:
                    problems.append(Problem(path, n, f"{kind} with an empty name: {m.group(0)!r}"))
                if body_text is None:
                    continue
                if body_text.strip() == "":
                    continue  # `@salt{}` is the documented way to say "some"
                q = QUANTITY.match(body_text)
                if q is None or not (q.group("amount") or "").strip():
                    problems.append(
                        Problem(path, n, f"{kind} quantity has no amount: {m.group(0)!r}")
                    )
                elif "%" in body_text and not (q.group("unit") or "").strip():
                    problems.append(
                        Problem(path, n, f"{kind} quantity has a % but no unit: {m.group(0)!r}")
                    )
        if "~" in line and not TIMER.search(line) and re.search(r"~(?!\{)", line):
            problems.append(Problem(path, n, "a timer needs braces, e.g. ~{10%minutes}"))
    return problems


def check_file(path: Path) -> list[Problem]:
    rel = str(path.relative_to(REPO_ROOT))
    text = path.read_text(encoding="utf-8", errors="replace")
    fm_lines, body_start, problems = split_front_matter(text, rel)
    if problems:
        return problems
    data, fm_problems = parse_front_matter(fm_lines, rel)
    problems += fm_problems
    problems += check_front_matter(data, rel)
    body = "\n".join(text.splitlines()[body_start - 1 :])
    problems += check_body(body, rel, body_start)
    if not body.strip():
        problems.append(Problem(rel, body_start, "the recipe has no steps"))
    return problems


def recipe_paths(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(p).resolve() for p in argv if p.endswith(".cook")]
    return sorted(RECIPES_DIR.rglob("*.cook"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)

    paths = recipe_paths(args.paths)
    if not paths:
        print("check_recipes: no .cook files to check")
        return 0

    problems: list[Problem] = []
    for path in paths:
        problems += check_file(path)

    if not problems:
        print(f"check_recipes: {len(paths)} recipe(s) OK")
        return 0

    print(f"check_recipes: {len(problems)} problem(s) in {len(paths)} file(s)\n", file=sys.stderr)
    for p in problems:
        print(p.render(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
