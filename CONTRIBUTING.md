# Contributing

```bash
make setup
```

That installs the git hooks. Two of them matter: one refuses anything staged
under `private/`, and one scans for the personal data a recipe collection leaks.
`SECURITY.md` is the full picture.

## Recipes and copyright — read this before adding one

This is the part people get wrong, so it is first. It matters more here than in
most recipe repositories, because this one is public and MIT-licensed: anything
committed is offered to strangers for reuse, and it is not yours to offer unless
it is yours.

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

`source` is a required field and the checker enforces it. For a recipe that is
your own, `Family recipe`, `Our own`, or `Invented for this repository` all pass.
Anything else has to actually name something — `adapted` or `family` on its own
will fail, because they tell a reader nothing about whose words they are reading.

## Other people's names

These recipes are published. Yours are yours to publish; the people around you
did not make that choice.

So: no real names, in a title, in `source`, or in a note. "Grandma Edith's pie"
publishes a real person's name and her relationship to you, permanently, in a
file that will outlive your interest in the pie. "Made this for Tom's birthday"
says who was in the house and when. Write the first as "Grandma's pie" — the
recipe is unchanged — and leave the second out.

The same goes for contact details, addresses, coordinates, links into private
storage, and anyone else's dietary or health information. Your own allergy is
yours to write down. Somebody else's is not.

If a recipe carries a story you want to keep but not publish, put the whole thing
in `private/`. It is gitignored and hook-refused, and Kitchen ERP still indexes
it, costs it, and shows it exactly like a published one. Nothing is lost.

**Fill in `tools/denylist.txt`.** It is gitignored, and until it has names in it
the scanner cannot catch any of this — a name is not a pattern, and no rule can
tell that "Edith" is your grandmother rather than a variety of apple. See
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

That parses every recipe, validates the front matter, runs the personal-data
scanner, and lints the documentation. The hooks run the same things, so a clean
`make check` means a clean commit. Never `--no-verify`.

If you edit the Markdown: wrap at 80 columns, give every fenced block a language
(`cook`, `bash` or `text`), and let heading levels increase one at a time.
Relative links are checked too, including `#anchors`, so renaming a heading that
another document points at fails rather than rotting quietly.

## Licence

MIT. By contributing you confirm the recipe text is your own or is in the public
domain, and that you are licensing it under MIT along with everything else here.
