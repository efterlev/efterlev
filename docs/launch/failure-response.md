# Launch-day failure-response playbook

Five scenarios, each with a triggered response. Don't improvise on launch day — if any of these fire, follow the playbook.

## 1. Critical bug report in the first hour

**Trigger:** an issue or HN comment surfaces a real bug — wrong version printed, install fails on a major platform, scan crashes, redaction misses an obvious secret pattern.

**Immediate response:**

1. Acknowledge publicly within 15 minutes. "Thanks — looking now. Will update within the hour." A public ack defuses; silence amplifies.
2. Reproduce locally. If you can't reproduce, ask the reporter for `efterlev --version`, OS, install method, and the exact command that failed.
3. Triage: scoped fix (5 minutes) or wide fix (hours)?
4. **Scoped fix path:** patch on a hot branch, cut `v0.1.1`, push artifacts, update the docs-site quickstart if affected.
5. **Wide fix path:** acknowledge the bug publicly with the canonical issue link; commit to a fix in the next release; offer the workaround if one exists.
6. Update the issue with status every 4 hours until closed.

**What NOT to do:** ship a quick fix that hasn't run through release-smoke.yml. The matrix exists for a reason; bypassing it on launch day is how a launch goes from "minor bug" to "broken installer for everyone."

## 2. Inflammatory comment from a competitor

**Trigger:** someone visibly affiliated with Paramify / compliance.tf / Vanta / etc. posts a dismissive or factually-misleading comment on HN, Reddit, or social.

**Immediate response:**

1. **Wait an hour before replying.** Most comments resolve themselves; the community handles bad-faith engagement better than a defensive maintainer can.
2. If the comment is factually wrong, reply with a single calm correction citing specific evidence (a doc page, a SPEC entry, a code link). Don't engage tone with tone.
3. Never delete or hide critical comments unless they violate the platform's rules. Visible defensiveness is worse than the criticism it's defending against.
4. If the comment escalates into harassment, follow the platform's reporting process. Don't engage personally.

**Tone reference:** the project's `COMPETITIVE_LANDSCAPE.md` is the model. Honest assessment, no FUD. Keep that posture in public exchanges.

## 3. Accidental secret in repo history discovered post-flip

**Trigger:** someone reports — either privately via SECURITY.md or publicly — that a real secret slipped past the launch grep-scrub and is in git history.

**Immediate response:**

1. **Rotate the secret immediately.** Assume it's compromised the moment it became public.
2. **Do NOT** force-push to rewrite history while the issue is still being assessed. Force-pushing public-repo history breaks every existing clone, fork, and link; the leak is already cached in GitHub's archive and forks.
3. Open a security advisory documenting:
   - What was leaked.
   - When it was committed.
   - When it was rotated (post-discovery time).
   - Whether evidence of exploitation exists.
4. If the leak is severe enough to warrant a rewrite (e.g., a private signing key still in use), use `git filter-repo` to scrub history and force-push. Communicate broadly: every clone, fork, and CI cache needs to be re-cloned. Coordinate with anyone who has a known fork.
5. Update `scripts/launch-grep-scrub.sh` to catch the pattern that was missed; the fix lands in the repo as a follow-up commit.

**Severity scale:**

- **Low:** test fixture with a fake-but-real-shape token; rotation suffices, no rewrite needed.
- **Medium:** customer-data reference (e.g., a real S3 bucket name); coordinate with the customer if any, scrub via filter-repo.
- **High:** private signing key, current AWS credentials, OIDC token; rotate, scrub, advisory, public post-mortem.

## 4. Surge of low-quality detector PRs

**Trigger:** the launch attracts contributors who open detector PRs that don't meet the contract — missing fixtures, no "does NOT prove" section, claiming KSI mappings that don't exist in FRMR.

**Immediate response:**

1. **Don't merge any PR that doesn't meet the contract**, even on launch day, even if the contributor is famous. Quality bar > contributor velocity.
2. Reply to each PR with the same template:
   - Thanks for the contribution.
   - The contract: link to `CONTRIBUTING.md` and the PR template checklist.
   - Specific gaps in this PR: missing X, Y, Z.
   - Offer: "If you're stuck on any of these, drop a Discussion and I'll help."
3. Mark PRs with the `needs-revision` label. Don't close — closing a contributor's first PR cold is the fastest way to lose them.
4. If a contributor opens a second incomplete PR after the feedback, escalate the docs: "I see this is your second PR with the same gap; here's the detector-writing tutorial..." → link to the deepened tutorial (which gets deepened in response to this exact feedback).

**What NOT to do:** lower the bar to grow contributor count. The whole project depends on detector quality being defensible to a 3PAO; a half-baked detector merged on launch day haunts every release after.

## 5. First report from a real user saying "this doesn't work on my infra"

**Trigger:** an actual user in our ICP — typically a DevSecOps lead or platform engineer — reports that Efterlev didn't work for them. Could be: install failed on their stack, scan produced zero findings on their (real, FedRAMP-relevant) Terraform, agent returned nonsense, secret redaction missed a real secret of theirs.

**This is the most important scenario.** A real user reaching out with real feedback is exactly what we're trying to elicit; respond accordingly.

**Immediate response:**

1. **Reply within an hour with curiosity, not defensiveness.** "Thanks — that's exactly the feedback we need. Can you share more about your stack?"
2. Move to a private channel if the user is willing — DM, email, or a private GitHub Discussion — so they can share details (sanitized Terraform snippets, scan output) without exposing their infra publicly.
3. Reproduce against their description on a fresh clone. If you can't reproduce, ask for sanitized fixtures.
4. Treat their feedback as the v0.2 design-partner channel. The 2026-04-22 archetype-only commitment specifically expected first-real-user feedback to drive v0.2 schema revisions; this is that moment.
5. Whether or not the bug gets fixed for v0.1.1, write up what you learned in a public retrospective. Other potential users see the response and learn what kind of project this is.
6. If the user becomes a serious design partner: open a private GitHub Discussion thread, schedule a 30-minute call, and start the v0.2 feedback-integration window per the launch plan's Phase C.

**What NOT to do:** dismiss the report ("works on my machine"), treat it as edge-case noise, or default to defensiveness. A real user reporting a real failure is gold; the response posture determines whether they (or anyone watching) ever come back.

---

## Escalation: when to pause the launch

Some failures warrant pausing the announcement sequence rather than pushing forward. Pause if:

- A critical bug is discovered that affects the install path on a major platform (macOS or Linux) and a fix isn't available within 2 hours.
- A real secret leak is discovered post-flip and warrants a history rewrite (the rewrite breaks any clones the announcement traffic would create).
- The release-smoke matrix continues to fail post-flip (Test PyPI publication broke, container build broke, etc.).

Pausing means: do not post to additional channels yet. Post a short notice on already-active channels: "Discovered an issue; investigating; updates in N hours." Resume the runbook after the fix lands and re-runs the smoke matrix.

A paused launch can be resumed without losing the long-term value of the release. A panicked-and-broken launch is much harder to recover from.
