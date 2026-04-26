# SPEC-57: Attestation artifact v1 — 3PAO review remediation omnibus

**Status:** drafted 2026-04-25 in response to the round-1 3PAO review of `attestation-20260425-203005.json`
**Gate:** post-A8 / pre-flip
**Depends on:** SPEC-13 (Documentation Agent), SPEC-12 (FRMR attestation generator)
**Blocks:** Post-launch confidence in the artifact's acceptability for real authorization packages
**Size:** M — three attestation-shape changes plus prompt + renderer + serializer + tests

## Why one omnibus spec

The 3PAO review (DECISIONS 2026-04-25, "Acting 3PAO review of generated FRMR attestation") produced six findings against the artifact. One was a blocker (walker traceability — fixed in commit `54e8b47`). One is a v0.2 polish (narrative-template consistency). The remaining four are attestation-artifact shape changes that share the same review trigger and should land together so the next artifact a maintainer generates carries all the improvements at once.

## Goal

The next FRMR attestation Efterlev produces should be acceptable to a 3PAO reviewing it for an authorization package, with no blocker findings and the High-severity observations addressed:

- A 3PAO can distinguish "scanner saw nothing because this KSI is procedural-only" from "scanner saw nothing because the CSP doesn't implement this KSI."
- A 3PAO sees, per KSI, both what FRMR maps AND what the scan actually evidenced — not one merged list that overstates evidenced coverage.
- A 3PAO can tell from the artifact's metadata which version of the attestation format produced it, independent of the FRMR catalog version. CR26 (mid-2026, est.) will likely bump FRMR; the attestation format version stays separate so downstream consumers can version-gate their parsers without conflating the two.

## Sub-specs

### SPEC-57.1 — Fifth GapStatus: `evidence_layer_inapplicable`

**Problem (3PAO §3):** `not_implemented` conflates two distinct failure modes — *the CSP genuinely doesn't implement this KSI* vs *the scanner cannot evidence this KSI from infrastructure-as-code by design*. KSI-AFR-FSI ("FedRAMP Security Inbox") is operational; KSI-PIY-* are policy commitments. An infrastructure scanner returning `not_implemented` for those is making a coverage statement, not a compliance finding. A 3PAO reviewing the artifact must currently distinguish the two by reading every narrative — the field-level signal hides the difference.

**Decision:** introduce `GapStatus = Literal["implemented", "partial", "not_implemented", "not_applicable", "evidence_layer_inapplicable"]`. The new value declares: the scanner has no reasonable path to evidence this KSI from the input modality (Terraform / OpenTofu source), AND no Evidence Manifest covers it. Reviewer action remains required to attest the KSI; the status communicates that the *tool's silence* is structural, not a finding.

**Where it touches:**
- `src/efterlev/agents/gap.py` — `GapStatus` literal expanded; `KsiClassification._positive_status_requires_evidence` validator also exempts the new status (it's another honest "no evidence cited" declaration).
- `src/efterlev/models/attestation_draft.py` — `AttestationStatus` literal expanded (parallel to GapStatus).
- `src/efterlev/agents/gap_prompt.md` — new section explaining when to use `evidence_layer_inapplicable`. The criterion is conservative: only when ALL of the KSI's FRMR-mapped 800-53 controls are pure-procedural (AT-*, PL-*, PS-*, PM-*, large parts of CA-*) AND no Evidence Manifest covers the KSI. The agent must NOT use this status when even one control could in principle be evidenced from IaC.
- `src/efterlev/reports/gap_report_html.py` (and the documentation/remediation HTML renderers) — new status-pill CSS class (`status-evidence_layer_inapplicable`) with a distinct color so a reviewer can scan and immediately see which "red" rows are real gaps vs coverage gaps.
- `src/efterlev/primitives/generate/generate_poam_markdown.py` — `evidence_layer_inapplicable` KSIs are skipped (they're not remediation items; same posture as `not_applicable`).
- Tests: per-status coverage in test_gap_report_html, test_documentation_report_html, test_remediation_report_html, test_generate_poam_markdown.

**Why not a deterministic algorithmic classifier:** "is this KSI evidenceable from IaC?" has gray areas (e.g., AC-3 has both procedural and infrastructure aspects). The agent makes the call with explicit criteria in the prompt, the same way it makes the implemented/partial/not_implemented call today. Future work could add a deterministic pre-filter that downgrades the agent's status from not_implemented to evidence_layer_inapplicable when the controls are all in the procedural-only set; that's a v0.2 hardening.

### SPEC-57.2 — Split `controls` into `controls_mapped` + `controls_evidenced`

**Problem (3PAO §5):** Each `AttestationArtifactIndicator.controls` field today is the FRMR-mapped controls list (everything the FRMR catalog says this KSI covers — for KSI-IAM-ELP that's 34 controls including IA-*, PS-*, SC-*). The narrative cites only AC-2/AC-3/AC-6 as actually evidenced. A 3PAO seeing a 34-control field next to a narrative that names 3 controls reads it as overclaiming.

**Decision:** split the single `controls` field into two:
- `controls_mapped: list[str]` — the FRMR catalog's controls list for this KSI (what's listed today). Preserved for reviewers who want the full mapping context.
- `controls_evidenced: list[str]` — the actual controls covered by the cited evidence. Computed from the union of `Evidence.controls_evidenced` across the citation set. Always a subset of `controls_mapped`.

`controls` (old field) is dropped — additive-only would leave both definitions ambiguous. SPEC-57.4 below documents this as the breaking change that drives `attestation_format_version: "1"`.

**Where it touches:**
- `src/efterlev/models/attestation_artifact.py` — `AttestationArtifactIndicator` schema change.
- `src/efterlev/primitives/generate/generate_frmr_attestation.py` — populate both fields.
- `src/efterlev/reports/documentation_report_html.py` — render both with clear labels.
- Existing tests need updates to assert on the new field names.

### SPEC-57.3 — `attestation_format_version` field

**Problem (3PAO §7):** The artifact's `info` block carries `frmr_version: "0.9.43-beta"` — the version of the upstream catalog. CR26 (mid-2026, est.) will bump FRMR. Downstream consumers parsing Efterlev's artifact need to version-gate against the *artifact format*, not the catalog. With one field, the two get conflated.

**Decision:** add `info.attestation_format_version: str = "1"`. Distinct from `frmr_version`. Bumped only when Efterlev makes a breaking change to the artifact shape (SPEC-57.2 is exactly that — splitting controls). SemVer-style major-only ("1", "2") rather than "1.0.0" because the artifact format is a contract surface, not a software version.

**Bump policy** (documented in the field's docstring):
- New optional fields → no bump.
- New required fields → bump (consumer parsers may break).
- Renamed/removed fields → bump.
- Semantic changes to existing field interpretations → bump.

The first bump is the SPEC-57 work itself: format version becomes "1". Pre-SPEC-57 artifacts implicitly have format version "0" — consumers parsing pre-SPEC-57 artifacts must default to "0" when the field is absent.

**Where it touches:**
- `src/efterlev/models/attestation_artifact.py` — new field on `AttestationArtifactInfo`.
- `docs/reference/frmr-attestation-schema.md` — bump-policy documentation.
- Tests for the existing artifact-generation path.

### SPEC-57.4 — DEFERRED to v0.2: narrative template consistency

**Problem (3PAO §6):** Per-KSI narratives vary in length and structure across status classes — some tight, some multi-paragraph with reviewer-action lists. A consistent template would help downstream review tooling do automated content checks.

**Why deferred:** this is a prompt-engineering polish that benefits from A/B-style iteration on real outputs. Locking a template now risks over-fitting to the dogfooded codebase shape. v0.2 work after launch produces enough sample artifacts to derive the right template empirically.

**Tracked here so it isn't lost.** v0.2 spec will be SPEC-57.4 (or a fresh spec referencing this entry).

## Roll-up exit criterion

- [ ] All four sub-specs (.1, .2, .3) implemented and tested.
- [ ] Re-running `efterlev agent document` on `terraform-aws-iam` (the 3PAO test target) produces an artifact with: the new `evidence_layer_inapplicable` status appearing on at least one of the procedural KSIs (KSI-AFR-FSI is the obvious candidate), `controls_mapped` and `controls_evidenced` both present with the latter ⊆ the former, and `info.attestation_format_version: "1"`.
- [ ] Re-walking the 3PAO review against the new artifact: §3, §5, §7 close (no longer findings); §6 deferred per SPEC-57.4 with explicit acknowledgment.

## Risks

- **Status proliferation.** Five statuses is a lot for a Pydantic Literal. Reviewer-facing UI (HTML pills, POA&M) needs visual clarity for each. Mitigation: the new status has a distinct color and a one-line legend in the rendered output's header.
- **Agent doesn't use the new status.** The Gap Agent might keep classifying procedural KSIs as `not_implemented` because the prompt change is subtle. Mitigation: the prompt explicitly enumerates the procedural-only control prefixes and gives one example KSI (KSI-AFR-FSI) as a positive case. If subsequent dogfooding shows the agent ignoring the new status, downgrade-not-implemented-to-evidence_layer_inapplicable can be added as a deterministic post-classification pass.
- **Format-version bumps cascade.** Once a v0 reads `"1"`, every later breaking change requires a bump and a parallel-parse path in any consumer. Mitigation: the bump policy is documented and conservative — most v0.2 changes will be additive (no bump). The main risk is when CR26 lands and FRMR shape changes; that's a coordinated bump documented in DECISIONS at the time.

## Open questions

- Should `controls_evidenced` be empty `[]` or omitted entirely when no evidence was cited (e.g., for a `not_implemented` KSI)? Resolution: always present, empty-list when absent. Consumers prefer a stable schema.
- Should the new status apply retroactively to existing v0 artifacts? Resolution: no. v0 artifacts stay v0. The new status is post-SPEC-57 only.
