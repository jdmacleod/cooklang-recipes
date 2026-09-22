# cooklang-recipes

[![Checks](https://github.com/jdmacleod/cooklang-recipes/actions/workflows/checks.yml/badge.svg)](https://github.com/jdmacleod/cooklang-recipes/actions/workflows/checks.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Plain-text recipes in [Cooklang](https://cooklang.org), laid out the way
[Kitchen ERP](https://github.com/jdmacleod/kitchen-erp) expects to find them.

This is a household's real recipe collection, published on purpose. Everything
under `recipes/` is meant to be read, cooked, and copied — that is what the MIT
licence is for.

Two things it deliberately does not carry. **Other people's details**: names of
relatives and friends, contact details, addresses. Publishing your own cooking is
your call; publishing somebody else's name is not. And **anything you would
rather keep**, which goes in `private/` — gitignored, refused by a commit hook,
and still indexed by Kitchen ERP exactly like a published recipe. Read
[`SECURITY.md`](SECURITY.md) before your first commit; the names scanner it
describes does nothing until you fill it in.

The recipes here at the start are written-for-the-repository examples, kept so
the format has something to demonstrate and the checks have something to run
against. Delete them as your own accumulate.

## The format

One recipe per `.cook` file. YAML front matter, then steps.

```cook
---
title: Weeknight chickpea stew
servings: 4
tags: [vegetarian, one-pot, weeknight]
source: Invented for this repository
---

Heat the @olive oil{2%tbsp} in a #large pot{} over medium heat.

Add the @yellow onion{1}, diced, and cook ~{8%minutes} until soft.
```

- `@ingredient{quantity%unit}` — braces are required for a multi-word name.
  `@salt{}` means "some", with no quantity.
- `#cookware{}` — the same rule about braces.
- `~{10%minutes}` — a timer. It always takes braces.
- `--` starts a comment to the end of the line.

Front matter takes `title` and `source` (both required), and optionally
`servings`, `tags`, `notes`, `course`, `time`, and `author`. There is **no id
field**: a recipe is identified by its path, and Kitchen ERP follows renames
through git history rather than by writing anything into the file. Nothing in
this repository is ever written to by the application.

`source` is required for a licensing reason, not a tidy one — see
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Layout

```
recipes/
  baking/
  basics/
  mains/
  sides/
private/          gitignored: real recipes, never committed
tools/            the checks
```

The directories are for humans. Kitchen ERP scans for `*.cook` anywhere under the
root, so you can reorganise freely; it follows the move through git history and
keeps each recipe's resolved ingredients attached.

## Checks

```bash
make setup     # install the git hooks
make check     # everything CI runs
```

- `make check-recipes` parses every file, validates the front matter, and fails
  on a malformed quantity or an unbalanced brace. A recipe that does not parse
  does not cost anything in Kitchen ERP, so it is worth catching here.
- `make check-personal` scans for the things a recipe collection leaks: email
  addresses, phone numbers, street addresses, coordinates, links into private
  storage, and a local denylist of names.

No dependencies. Python 3 and git, nothing else.

## Using it with Kitchen ERP

Point `RECIPES_PATH` at a checkout. It is mounted read-only; the application
indexes it and never writes to it.

```bash
# in kitchen-erp/.env
RECIPES_PATH=../cooklang-recipes
```

## Licence

MIT — see [`LICENSE`](LICENSE). That covers the recipe text in this repository,
which is all original. It does not and cannot license anything you add from
somewhere else; see [`CONTRIBUTING.md`](CONTRIBUTING.md) before adding a recipe
from a book or a website.
