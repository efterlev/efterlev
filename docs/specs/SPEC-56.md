# SPEC-56: A8 launch rehearsal — omnibus

**Status:** implemented 2026-04-25 — all 5 artifacts landed; rehearsal-walkthrough is the closing maintainer action before the public flip
**Gate:** A8
**Depends on:** A1 through A7 all complete
**Blocks:** Public launch (the repo flip from private to public)
**Size:** M — five operational artifacts plus a script.

## Why one omnibus spec

A8 is launch-day operational prep. Five small artifacts that fit together as a single launch sequence: the pre-flight check (grep-scrub), the launch runbook, the failure-response playbook, the announcement copy, and the design-partner outreach. Separating each into its own spec file would scatter the launch-day mental model.

## Goal

When the maintainer is ready to flip the repo public, every operational decision has already been made and rehearsed:

- A scripted grep sweep confirms no NDA-era / private-repo language slipped through.
- A runbook walks the launch hour-by-hour from "Monday morning, ready to flip" through "Day 7 retrospective."
- A failure-response playbook names the five most likely first-hour failures with concrete responses.
- Announcement copy is drafted but not yet posted — the maintainer reviews and customizes minutes before launch.
- Design-partner outreach emails are drafted to five named ICP targets, ready to send Day 2 of launch week.

The launch is gate-driven (not date-driven per the open-source posture in `DECISIONS.md` 2026-04-23), so this spec doesn't commit to a date. It's the readiness layer that converts "every gate is closed" into "we are publicly live."

## Sub-specs

### SPEC-56.1 — Pre-flip grep/scrub checklist + script ✅ (landed 2026-04-25)

`docs/launch/grep-scrub-checklist.md` documents what's checked. `scripts/launch-grep-scrub.sh` runs the checks.

The script greps the entire repo for:

- NDA-era / private-repo-era language: "NDA", "closed-source", "private repo", "v1 public-repo opening", "external contributions paused"
- Internal hostnames or accidental real-customer references
- Any string matching common secret patterns the secret-redaction library already covers — defense in depth at git-history-time
- Stale references to `lhassa8/Efterlev` or `lhassa8/efterlev` that should be `efterlev/efterlev`

Exit 0 = clean, exit 1 = at least one finding (with line+context). Maintainer reviews each finding; benign matches (DECISIONS.md historical entries that legitimately discuss the rescinded closed-source lock, etc.) get an explicit allowlist comment with rationale.

### SPEC-56.2 — Launch runbook ✅ (landed 2026-04-25)

`docs/launch/runbook.md` — hour-by-hour sequence from "ready to flip" through Day 7 retrospective. Covers:

- The flip itself (private → public, tag v0.1.0, push artifacts).
- Announcement sequence (HN, social, subreddits, Slacks).
- Day 1: blog post on docs site.
- Day 2: design-partner outreach.
- Day 3: open `good first issue` tickets.
- Day 7: public retrospective via GitHub Discussions.
- 30-day success gates (revisit of green / yellow / red criteria from the launch plan).

### SPEC-56.3 — Failure-response playbook ✅ (landed 2026-04-25)

`docs/launch/failure-response.md` — first-hour scenarios + responses:

1. Critical bug report in the first hour after launch.
2. Inflammatory comment from a competitor.
3. Accidental secret in repo history discovered post-flip.
4. Surge of low-quality detector PRs.
5. First report from a real user saying "this doesn't work on my infra."

Each scenario: trigger conditions, immediate response, follow-up actions, when (if ever) to escalate.

### SPEC-56.4 — Announcement copy ✅ (landed 2026-04-25)

`docs/launch/announcement-copy.md` — drafts ready for the maintainer to customize at launch:

- HN "Show HN" post title + body (300 words max).
- Reddit posts: r/devops, r/govcloud, r/fednews, r/cybersecurity. Different framing per subreddit.
- LinkedIn post.
- dev.to / Medium cross-post (longer, narrative).
- Blog post for the docs site itself ("Why we built Efterlev").

### SPEC-56.5 — Design-partner outreach email templates ✅ (landed 2026-04-25)

`docs/launch/design-partner-outreach.md` — five named ICP-A targets with personalized opening lines and a shared body. Templates emphasize:

- Concrete value prop ("we just shipped X — looks like you'd benefit from Y").
- Low-friction ask ("try it once, give us 30 minutes of feedback").
- No sales pressure (pure-OSS posture means there's nothing to sell).
- Pointer to GitHub for self-service.

## Roll-up exit criterion (gate A8)

- [x] All 5 sub-deliverables landed (2026-04-25).
- [x] `scripts/launch-grep-scrub.sh` runs against the current repo and exits 0 (`RESULT: clean. Repo passes pre-flip grep-scrub.`, 2026-04-25). Allowlist entries cover (a) historical NDA/closed-source references in DECISIONS.md / SPEC files / launch artifacts, (b) the technical-vocabulary "confidentiality" used in CIA-triad and FRMR mappings, and (c) the vendored NIST 800-53 catalog's compliance-framework prose.
- [ ] A maintainer other than the BDFL (or, in BDFL-era, the BDFL with fresh eyes after a 24-hour pause) walks the launch runbook end-to-end on a staging fork and reports zero surprises.
- [ ] All A1-A7 maintainer-action queues have been worked through (Docker Hub org claimed, npm namespace held, repo transferred to `efterlev/efterlev`, branch protection applied, DCO app installed, security review filled in, GovCloud walkthrough completed if maintainer has access).

## Risks

- **Launch-day adrenaline.** Pressure leads to skipping checklist steps. Mitigation: the runbook is checklist-shaped, not narrative; each item has a checkbox the maintainer ticks. Skipping is then visible.
- **Grep-scrub false negatives.** The script can miss things it doesn't know to look for. Mitigation: the maintainer also runs a final eyeball pass on `git log --oneline | head -20` and `git diff main..HEAD --stat` before flipping; nothing replaces a human read.
- **Announcement copy stale by launch time.** Drafted now, the references to "FedRAMP 20x Phase 2 just authorized N pilot participants" will date. Mitigation: the templates flag the dynamic phrases for refresh-at-launch-time; the maintainer plugs in current numbers minutes before posting.

## Open questions

- Should we coordinate launch with another OSS project's announcement (e.g., a govnotes-demo refresh or a friendly tool's release)? Answer: no. Launch on its own merits; coordination adds dependencies that can drift.
- Do we send the announcement to the Anthropic Claude team (since we're an Anthropic-flavored project)? Answer: optional, BDFL judgment; not part of the runbook.
