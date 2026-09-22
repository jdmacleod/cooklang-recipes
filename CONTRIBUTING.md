# Contributing

```bash
make setup
```

That installs the git hooks. Two of them matter: one refuses anything staged
under `private/`, and one scans for the personal data a recipe collection leaks.
`SECURITY.md` is the full picture.

## Recipes and copyright — read this before adding one

This is the part people get wrong, so it is first.

In the United States, **a list of ingredients is not copyrightable**, and neither
is a bare functional procedure. *Publications International v. Meredith* (7th
Cir. 1996) is the usual citation. What **is** copyrightable is the *expression*
around it: the headnote, the descriptive prose, the storytelling, the particular
wording and rhythm of the steps, the photographs, and the selection and
arrangement of a collection as a whole.

So, for anything that did not originate with you:

- **Never paste a recipe in.** Not the headnote, not the method, not "just the
  ingredients and a couple of lines". Copying a book's method verbatim into a
  public MIT-licensed repository is republishing it.
- **Write the method in your own words**, from having cooked it. Quantities and
  temperatures are facts and carry over freely; sentences do not.
- **Credit the original in `source`.** Title, author, and where it was published.
  Attribution is not a licence — it does not make copying lawful — but a recipe
  you rewrote and credited is both honest and legal, and the credit is how a
  reader finds the original.
- **A photograph is never fair game**, and every image format is gitignored here
  anyway.
- When in doubt, leave it in `private/`. Nothing is lost: Kitchen ERP indexes
  `private/` exactly the same way.

`source` is a required field and the checker enforces it. `Invented for this
repository` is the value for something original. Anything else has to actually
name something — `adapted` or `family` on its own will fail the check, because
they tell a reader nothing about whose words they are reading.

## No real people

The public corpus has no real names in it. Not in a title, not in `source`, not
in a note. "Grandma Edith's pie" names a living or once-living person in a public
repository, and "made this for Tom's birthday" says who was in the house and
when.

If a recipe genuinely came from a relative and you want to keep that, it belongs
in `private/`. The synthetic corpus exists to demonstrate the format, and it does
that just as well with an invented name.

Add the names you care about to `tools/denylist.txt` — gitignored — so the
scanner catches the mistake instead of a stranger doing it for you. See
SECURITY.md.

## Writing a recipe

```cook
---
title: Braised carrots
servings: 4
tags: [side, vegetarian]
source: Invented for this repository
---

Melt the @unsalted butter{30%g} in a #wide pan{} over low heat.

Add the @carrots{500%g}, sliced into coins, with @water{100%ml} and a pinch of
@flaked sea salt{}. Cover and cook ~{15%minutes}.
```

- Braces are required whenever a name is more than one word: `@olive oil{}`, not
  `@olive oil`.
- `@salt{}` is the documented way to say "some, to taste".
- A timer always takes braces: `~{10%minutes}`, never `~10 minutes`.
- Name ingredients the way you would say them, not the way a shop labels them.
  Kitchen ERP normalizes `raw_name` and resolves it to a catalog ingredient once,
  then remembers; consistency between recipes helps that, and brand names hurt it.
- Units should be ones a unit table knows: `g`, `kg`, `ml`, `l`, `tsp`, `tbsp`,
  `cup`, `oz`, `lb`, or a count. A measure word like `cloves` is fine as text.
- One recipe per file. Filenames are kebab-case and are the recipe's identity, so
  renaming one is a real change — git tracks the move and Kitchen ERP follows it.

## Before you commit

```bash
make check
```

That parses every recipe, validates the front matter, and runs the personal-data
scanner. The hooks run the same things, so a clean `make check` means a clean
commit. Never `--no-verify`.

## Licence

MIT. By contributing you confirm the recipe text is your own or is in the public
domain, and that you are licensing it under MIT along with everything else here.
