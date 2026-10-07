# English translation

This repository is a **fork** of [E2r7hN07Fl47/unmuda](https://github.com/E2r7hN07Fl47/unmuda),
taken at upstream commit `fcaa9dc`, with the Russian documentation and tool
output translated into English.

None of this is new research. The Kyocera DIAG backdoor, the `LOOTBFCK` service
magic, the CVE-2024-31317 chain and every finding in the guides are the upstream
authors' work - see **Authors** in [README.en.md](README.en.md).

## What this fork adds

| Path | What it is |
|---|---|
| `README.en.md` | translation of `README.md` |
| `TOOLS.en.md` | translation of `TOOLS.md` |
| `CODE-COMMENTS.en.md` | line-keyed English reference for the Russian comments in `tools/*.py` |
| `guide/*.en.md` | translations of `guide/*.md` |
| `unlock.en.sh` | `unlock.sh` with English strings; same logic, same commands |
| `tools/*.py` (branch `en`) | the tools with English docstrings, comments and runtime output |

The Russian originals are untouched and remain the authoritative text. Where a
translation and the original disagree, the original wins.

## Branches

- `main` - upstream files plus the English **documentation** only. No existing
  file's behaviour changes, so this is what an upstream pull request would carry.
- `en` - `main` plus the `tools/*.py` translation. That one *replaces* the tools'
  Russian runtime output, so it is kept off `main` until upstream agrees on how
  to ship it.

## Changes from upstream

Modifications, with dates (GPL-3.0 §5(a)):

- **2026-10-07** - Russian prose, code comments and printed strings translated to
  English: the documentation files listed above, plus `tools/*.py` on branch `en`.
- **2026-10-07** - `.gitignore` (branch `en`): also ignore `p31317.txt` and
  `chkcode_zero.img`, both generated at run time and not meant to be published.

## Licence

Unchanged: **GPL-3.0** (see [LICENSE](LICENSE)). A translation is a derivative
work, so this fork stays under the same licence.
