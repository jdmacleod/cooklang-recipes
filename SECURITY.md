# Privacy and this repository

A recipe collection is not obviously personal data, which is exactly what makes
it worth writing this down.

A receipt identifies a household through numbers — a loyalty card, an address, a
coordinate. A recipe collection identifies it through *people and occasions*.
Who the dish is named after. Who was at the table. Whose allergy the substitution
is for. What the household eats every week, and what it stopped eating in March.
None of that looks like a pattern, and none of it can be caught by a rule that
looks for digits.

So the line here is drawn by directory, not by cleverness:

**`recipes/` is public and entirely invented. `private/` is real and never leaves
the machine.**

## What lives where

| | `recipes/` | `private/` |
|---|---|---|
| Committed | Yes | Never |
| Content | Recipes written for this repository | The household's own recipes |
| Names of real people | Never | However you like |
| Notes about occasions, guests, health | Never | However you like |

`private/` is denied in `.gitignore`, and `tools/no_private_dir.py` refuses any
staged path under it even via `git add -f`, because `.gitignore` alone does not
survive a `-f`. Kitchen ERP scans for `*.cook` anywhere under the mount, so a
recipe in `private/` works in the application exactly like a public one. It is
simply not published.

If you would rather not have real recipes in the same checkout as a public
repository at all, keep them in a separate private repository and point
`RECIPES_PATH` at that instead. Nothing here depends on the two being together.

## What the scanner covers

`tools/scan_personal.py` runs on commit and in CI, in two tiers.

**Rules**, for what looks like a pattern:

| Rule | Catches |
|---|---|
| `EMAIL` | Any address outside `example.com`/`.org`/`.net`. |
| `PHONE` | Any number outside the reserved 555 exchange. |
| `STREET` | Numbered street addresses. |
| `COORDS` | Coordinate pairs, which identify a household as surely as an address. |
| `LOCAL_PATH` | Absolute paths under a home directory, which leak the account name. |
| `PRIVATE_URL` | Links into Google Photos, Drive, iCloud, Dropbox, OneDrive, Notion. Unlisted is not private once the link is in a public repository. |

**A literal denylist**, for what does not: the names of the people who cook here,
the friends and relatives a recipe is credited to, and their contact details.
This is the tier that matters most and the only one that can catch "Grandma
Edith's pie".

The names themselves are never committed. `tools/denylist.txt` is gitignored;
`tools/denylist.hashes` **is** committed and holds a salted SHA-256 of each
entry, with the salt living only in the gitignored `tools/denylist.salt` and in
the `RECIPES_DENYLIST_SALT` repository secret. GitHub holds the digests in one
place and the salt in another, and neither is worth anything without the other.
A pull request from a fork gets no secret and runs the rules tier only, which is
a deliberate downgrade rather than a failure. A public canary string in the file
is checked on every run, so a mistyped secret fails loudly instead of looking
like a clean scan.

Start it with:

```bash
cp tools/denylist.example.txt tools/denylist.txt   # gitignored
$EDITOR tools/denylist.txt                          # one name per line
make denylist                                       # regenerates the digests
```

## Suppressions

A finding that is genuinely benign is suppressed one line at a time, with a
reason written down:

```cook
A dish we first had at Cafe Verano.  -- scan: allow invented place
```

Never suppress a whole file, never disable a rule to make CI green, and never
commit with `--no-verify`.

## Photographs

Every image format is denied in `.gitignore`. No scanner can read pixels, and a
photograph of a finished dish on a kitchen table is a photograph of a kitchen,
often with a window in it. If this repository ever wants images, they come from
somewhere that was staged for the purpose, and the denial is lifted with a check
attached — not quietly.

## If something real has been committed

Stop. Do not push. Do not try to rewrite history alone — removing a file from
history needs `git filter-repo` and a forced push that every clone has to
follow. Raise it through GitHub's private vulnerability reporting on this
repository.
