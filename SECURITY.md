# Privacy and this repository

**These are a real household's recipes, published on purpose.** That is the
owner's decision and it is not the thing this document is here to argue with.
What it is here for is the part that decision does *not* cover.

Publishing what you cook discloses more than a list of dishes. Taken as a
collection rather than one file at a time, a recipe repository says roughly how
many people eat here (servings), what they cannot eat (substitutions and
omissions), what they observe (what is never present), when the household is
busy (what is tagged weeknight), and how all of that changes over time, because
git keeps every version. None of that is dangerous on its own. All of it is
worth having decided rather than discovered.

The rule that follows:

**Publishing your own cooking is your call. Publishing somebody else's details
is not.**

## What must not be committed, regardless

A recipe you own can still carry things that belong to other people. These never
go in, and the scanner looks for them on every commit:

- **Other people's names.** The relative a dish came from, the friend who
  brought it, the guest it was made for. "Grandma Edith's pie" publishes a real
  person's name and her family connection to you, in a file that outlives your
  interest in the recipe. Write it as "Grandma's pie" and put the rest in
  `private/`, or in nothing at all.
- **Contact details.** Email addresses, phone numbers — yours or anyone's.
- **Addresses and coordinates.** A street address or a lat/long pair identifies a
  household as surely as a name does, and better.
- **Links into private storage.** A Google Photos or Dropbox link is unlisted,
  not private, and it stops being either once it is in a public repository.
- **Health and dietary information about other people.** Your own allergy is
  yours to publish. Somebody else's is not.

## `private/`

`private/` is the opt-out. Anything in it is gitignored, refused by a commit hook
even under `git add -f`, and never published — while still being indexed by
Kitchen ERP exactly like a public recipe, because the application scans for
`*.cook` anywhere under the mount.

Use it for the recipes you would rather not publish: the ones with another
person's name on them, the ones that carry a story you do not want indexed, the
ones that are somebody else's to share. Nothing is lost by putting a recipe
there — it still costs out, still resolves its ingredients, still appears in the
application. It simply is not on the internet.

## What the scanner covers

`tools/scan_personal.py` runs on commit and in CI, in two tiers.

**Rules**, for what looks like a pattern:

| Rule | Catches |
|---|---|
| `EMAIL` | Any address outside `example.com`/`.org`/`.net`. |
| `PHONE` | Any number outside the reserved 555 exchange. |
| `STREET` | Numbered street addresses. |
| `COORDS` | Coordinate pairs. |
| `LOCAL_PATH` | Home-directory paths, which leak the account name. |
| `PRIVATE_URL` | Links into Google, iCloud, Dropbox, OneDrive or Notion. |

**A literal denylist**, for what does not look like a pattern: the names of the
people around this household, and their contact details.

> **This tier is the one that matters, and it does nothing until you fill it in.**
> A name is not a pattern. No rule can tell that "Edith" is your grandmother
> rather than a variety of apple. If `tools/denylist.txt` is empty, the scanner
> cannot catch the single most likely way a real recipe collection exposes
> somebody — and in a public repository of real recipes, that is the whole risk.

```bash
cp tools/denylist.example.txt tools/denylist.txt   # gitignored
$EDITOR tools/denylist.txt                          # one name per line
make denylist                                       # regenerates the digests
```

Put in the first names and surnames of everyone in the household, and of the
relatives and friends whose recipes are in here. Prefer a distinctive name over a
very common one, which will match constantly and teach you to suppress the rule.

The names themselves are never committed. `tools/denylist.txt` is gitignored;
`tools/denylist.hashes` **is** committed and holds a salted SHA-256 of each
entry, with the salt living only in the gitignored `tools/denylist.salt` and in
the `RECIPES_DENYLIST_SALT` repository secret. GitHub holds the digests in one
place and the salt in another, and neither is worth anything without the other.
A pull request from a fork gets no secret and runs the rules tier only, which is
a deliberate downgrade rather than a failure. A public canary string in the file
is checked on every run, so a mistyped secret fails loudly instead of looking
like a clean scan.

## Suppressions

A finding that is genuinely benign is suppressed one line at a time, with a
reason written down:

```cook
A dish we first had at Cafe Verano.  -- scan: allow restaurant, not a person
```

Never suppress a whole file, never disable a rule to make CI green, and never
commit with `--no-verify`.

## Photographs

Every image format is denied in `.gitignore`. No scanner can read pixels, and a
photograph of a finished dish on a kitchen table is a photograph of a kitchen,
usually with a window and often with a person in it. If this repository ever
wants images, the denial is lifted with a check attached — not quietly.

## Git remembers

Everything here is permanent once pushed. A recipe you publish and later delete
stays in history, and so does a name you committed and then edited out. Removing
something for real needs `git filter-repo` and a forced push that every clone has
to follow.

So: if you are unsure about a file, it goes in `private/` first. Moving a recipe
from `private/` to `recipes/` later is one `git mv`. Moving it back is not.

## If something has been committed that should not have been

Stop. Do not push. Do not try to rewrite history alone. Raise it through GitHub's
private vulnerability reporting on this repository.
