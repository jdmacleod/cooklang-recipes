#!/usr/bin/env python3
"""Refuse to commit anything under private/.

`.gitignore` already denies it, but `git add -f` overrides `.gitignore` and a
commit hook does not. This is the second line under the opt-out: the recipes this
household has chosen not to publish live in private/ and never leave the machine,
while Kitchen ERP still indexes them from there.

Invoked by pre-commit with the staged paths.
"""

from __future__ import annotations

import sys
from pathlib import Path

FORBIDDEN = ("private",)


def main(argv: list[str]) -> int:
    bad = [p for p in argv if Path(p).parts and Path(p).parts[0] in FORBIDDEN]
    if not bad:
        return 0
    print("Refusing to commit files under a private directory:", file=sys.stderr)
    for p in bad:
        print(f"  {p}", file=sys.stderr)
    print(
        "\nprivate/ is for the recipes this household does not publish. Kitchen ERP"
        "\nindexes them from there exactly the same way. If this one is meant to be"
        "\npublished, move it under recipes/ instead.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
