# Pre-flip grep-scrub checklist

Before flipping the repo from private to public, run this script and review every finding. The script is at `scripts/launch-grep-scrub.sh`; the allowlist at `scripts/launch-grep-scrub.allowlist`.

```bash
bash scripts/launch-grep-scrub.sh
```

Expected output: `RESULT: clean. Repo passes pre-flip grep-scrub.`

## What it checks

1. **NDA-era / closed-source-era language.** The closed-source-through-v1 lock was rescinded 2026-04-23 (`DECISIONS.md`); any user-facing claim that the project is still closed is stale.
2. **Stale URL references.** Pre-transfer references to `lhassa8/Efterlev`. Should all be `efterlev/efterlev`.
3. **Secret-shaped strings in committed files.** Defense-in-depth on top of the runtime LLM-prompt scrubber. Catches AWS access key shapes, Anthropic key prefixes, GitHub tokens, PEM private-key blocks.
4. **Stale internal-status language.** "Internal only," "confidential," "do not distribute" markers.
5. **Stale test counts.** README's "X tests passing" line drifts as tests are added; the script catches the historical values so you don't ship with stale numbers.

## When the script reports findings

For each finding the script reports:

- **Triage:** is this a stale claim (fix the doc), a historical-record entry (allowlist with a comment), or a real secret (rotate immediately, then `git filter-repo` to scrub history)?
- **Fix or allowlist.** Stale claims get fixed in a normal PR. Historical-record entries get an allowlist line in `scripts/launch-grep-scrub.allowlist` with a comment explaining why the match is benign.
- **Re-run.** The script is idempotent; re-run until exit 0.

## Final eyeball pass

The script catches what it knows to look for. Two things it doesn't catch:

- **`git log --oneline | head -30`** — read the recent commit messages. Anything that reads like internal-only chatter ("WIP," "fixup for the broken thing Bob mentioned") is fine for a private repo, awkward for a public one.
- **`git diff main..HEAD --stat`** — if any file's listed as massively changed, eyeball it. Last-minute changes are how surprises ship.

## Re-running pre-flip

The script is run by the maintainer at A8 launch rehearsal AND immediately before the actual flip on launch day (after any final touch-ups). If the maintainer has stepped away from the repo for more than a few hours since the last clean run, re-run.
