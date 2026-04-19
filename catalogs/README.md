# catalogs/

Source materials vendored into the repo for determinism and air-gap friendliness.
`efterlev init` references these files in place rather than downloading at runtime.
An `efterlev catalog update` command is planned for v1 for users who want the latest;
v0 ships with a known-good pinned set.

Two inputs ship today, each serving a different layer of the model:

- **FedRAMP FRMR (primary)** — the FedRAMP Machine-Readable data that defines the
  Key Security Indicators (KSIs) our detectors evidence, plus the FedRAMP
  requirements and definitions the 20x authorization process is built around.
- **NIST SP 800-53 Rev 5 catalog (underlying)** — the control catalog that
  every KSI indicator references via its `controls` field. Load-bearing even
  though KSIs are the user-facing surface, because an auditor reading an
  Efterlev finding needs to see both layers: "this detector evidences
  KSI-SVC-SNT, which maps to 800-53 sc-8 and sc-13."

## Current contents

- `frmr/FRMR.documentation.json` — the authoritative FRMR file. Contains
  `info`, `FRD` (definitions), `FRR` (requirements), and `KSI` (11 themes,
  60 indicators) for both FedRAMP 20x and Rev5. KSIs are 20x-only; Rev5
  authorizations do not use the KSI layer.
- `frmr/FRMR.md` — structural guide from the upstream repo; useful reference
  when shaping the internal `Indicator` / `Theme` / `Baseline` models.
- `frmr/FedRAMP.schema.json` — JSON Schema (draft 2020-12) that validates
  `FRMR.documentation.json`. Used by the FRMR loader primitive for validation.
- `nist/NIST_SP-800-53_rev5_catalog.json` — NIST SP 800-53 Rev 5.2.0 OSCAL
  catalog. Resolved by `compliance-trestle`.

## A note on the archived GSA OSCAL source

Earlier plan documents cited `GSA/fedramp-automation` (path
`dist/content/rev5/baselines/json/FedRAMP_rev5_MODERATE-baseline_profile.json`)
as the canonical FedRAMP Moderate OSCAL profile. That repository was archived
in mid-2025 and its OSCAL baseline content was removed as FedRAMP transitioned
to FRMR under FedRAMP 20x. This vendoring replaces it: FRMR + the 800-53 catalog
cover the same ground via KSIs, and users who need OSCAL for Rev5 transition
submissions will get it from the v1 OSCAL output generator rather than from a
vendored FedRAMP-specific profile.

## Provenance record

Every vendored file records its source repository, commit SHA, download date,
file size, and SHA-256 so the vendored state is reproducible and tamper-evident.

| File | Source repo | Commit SHA | Downloaded | Bytes | SHA-256 |
| ---- | ----------- | ---------- | ---------- | ----- | ------- |
| `frmr/FRMR.documentation.json` | [`FedRAMP/docs`](https://github.com/FedRAMP/docs) | `a06fa8f9b103c0346895fb669b721962f5891bb6` | 2026-04-19 | 341,418 | `bbb734e9acb5a7ad48dafd6b2f442178f2b507c78c46b897cc4b1852c746c7c4` |
| `frmr/FRMR.md` | [`FedRAMP/docs`](https://github.com/FedRAMP/docs) | `a06fa8f9b103c0346895fb669b721962f5891bb6` | 2026-04-19 | 4,532 | `43aa72808f63d5e49055f47434ee273654cb09fe80b0e5eb02401a02dc9f1e8d` |
| `frmr/FedRAMP.schema.json` | [`FedRAMP/docs`](https://github.com/FedRAMP/docs) | `a06fa8f9b103c0346895fb669b721962f5891bb6` | 2026-04-19 | 13,235 | `1301497c55c6c188b8ba6c1236dc2d7c73286b55dc2ca5e6013ad38f0ba75f0c` |
| `nist/NIST_SP-800-53_rev5_catalog.json` | [`usnistgov/oscal-content`](https://github.com/usnistgov/oscal-content) | `bc8a528770033611df899b3d52703fb3dc91a20d` | 2026-04-19 | 10,441,264 | `1645df6a370dcb931db2e2d5d70c2f77bc89c38499a416c23a70eb2c0e595bcc` |

FedRAMP-produced content is U.S. federal government work and is not subject to
copyright under 17 USC §105. Redistribution within this repo is therefore
unencumbered; we preserve provenance for traceability, not as a licensing
condition.
