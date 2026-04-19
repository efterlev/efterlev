# catalogs/

FedRAMP and NIST OSCAL source materials vendored into the repo for determinism and air-gap
friendliness. `efterlev init` references these files in place rather than downloading at
runtime. An `efterlev catalog update` command is planned for v1 for users who want the latest;
v0 ships with a known-good pinned set.

## Current contents

- `nist/NIST_SP-800-53_rev5_catalog.json` — the NIST SP 800-53 Rev 5 controls catalog (parent
  of the FedRAMP Moderate profile). Used as the smoke-test artifact for trestle and, during
  the hackathon, as the catalog resolved by whichever profile we ultimately vendor.

## Pending: FedRAMP Moderate profile

The FedRAMP Moderate OSCAL profile is **not yet vendored**. The canonical source previously
referenced across `CLAUDE.md`, `README.md`, and the planning docs — `GSA/fedramp-automation`
at `dist/content/rev5/baselines/json/FedRAMP_rev5_MODERATE-baseline_profile.json` — no longer
resolves (GitHub returns 404). Public reporting indicates the repository was archived in
mid-2025 and a subsequent release removed the OSCAL baseline content as FedRAMP transitioned
toward the FedRAMP Machine-Readable (FRMR) format under the FedRAMP 20x initiative.

Resolution is tracked as an open pre-hackathon decision. See `DECISIONS.md` (entry tagged
`[scope]`) for the options under consideration.

## Provenance record

Every vendored file records its source repository, commit SHA, download date, file size, and
SHA-256 so the vendored state is reproducible and tamper-evident.

| File | Source repo | Commit SHA | Downloaded | Bytes | SHA-256 |
| ---- | ----------- | ---------- | ---------- | ----- | ------- |
| `nist/NIST_SP-800-53_rev5_catalog.json` | [`usnistgov/oscal-content`](https://github.com/usnistgov/oscal-content) | `bc8a528770033611df899b3d52703fb3dc91a20d` | 2026-04-19 | 10,441,264 | `1645df6a370dcb931db2e2d5d70c2f77bc89c38499a416c23a70eb2c0e595bcc` |
