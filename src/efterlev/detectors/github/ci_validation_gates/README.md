# github.ci_validation_gates

Detects whether `.github/workflows/*.yml` workflows include automated
IaC-validation steps. Reports per-workflow whether validation tooling
runs — `terraform validate`, `terraform plan`, `tflint`, `tfsec`,
`checkov`, or `trivy config`.

This is the first detector in the **`github-workflows`** source category
(Priority 1.2 of the v1 readiness plan). It treats each workflow file as
a "resource" the way Terraform detectors treat `aws_*` blocks.

## What it proves

- **CM-3 (Configuration Change Control)** — a workflow exists in CI; the
  customer is using version-controlled change management at all.
- **CM-3(2) (Test, Validate, Document Changes)** — when the workflow
  contains an IaC-validation step, the customer is performing automated
  pre-deployment validation. This is the canonical KSI-CMT-VTD signal.

## What it does NOT prove

- **That the validation step fails the build.** Some workflows run
  `terraform validate` but proceed regardless of its exit code. We
  detect the presence of the step, not the failure-on-error wiring.
- **That branch protection requires this workflow.** A workflow that
  validates but isn't a required check on `main` is advisory, not
  gating. Branch-protection wiring is a separate (planned) detector.
- **That validation findings are reviewed.** We check tooling presence,
  not review process. Follow-up: a detector that checks for an
  `actions/upload-artifact` step preserving the validation output.
- **Action-shaped validation beyond a small allow-list.** The detector
  recognizes `tfsec`, `checkov`, and `tflint` in `uses:` action names.
  Other action-shaped validation (e.g. KICS) isn't recognized; add to
  the allow-list as needed.

## KSI mapping

**KSI-CMT-VTD ("Validating Throughout Deployment").** FRMR 0.9.43-beta
lists CM-3, CM-3(2), CM-4(2), and SI-2 in this KSI's `controls` array.
This detector evidences CM-3 and CM-3(2) directly. CM-4(2) (verification
of controls implementation) and SI-2 (flaw remediation) are adjacent and
tracked for follow-up repo-metadata detectors.

## Validation states

| State | Meaning | Controls evidenced |
|---|---|---|
| `present` | At least one validation tool found in step `run:` or `uses:` | CM-3, CM-3(2) |
| `absent` | Workflow runs but no validation tool detected | CM-3 alone (with gap) |

`absent` Evidence carries a `gap` field naming the tools the detector
looked for, so a 3PAO reading the report knows what would have evidenced
the KSI.

## Tools recognized

`run:`-step substrings:
- `terraform validate`
- `terraform plan`
- `tflint`
- `tfsec`
- `checkov`
- `trivy config`

`uses:`-action substrings (canonical-tool name attributed):
- `tfsec` (e.g. `aquasecurity/tfsec-action`)
- `checkov` (e.g. `bridgecrewio/checkov-action`)
- `tflint` (e.g. `terraform-linters/setup-tflint`)

## Example

Input (`.github/workflows/ci.yml`):

```yaml
name: CI
on: [pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: terraform validate
      - uses: aquasecurity/tfsec-action@v1
```

Output:

```json
{
  "detector_id": "github.ci_validation_gates",
  "ksis_evidenced": ["KSI-CMT-VTD"],
  "controls_evidenced": ["CM-3", "CM-3(2)"],
  "content": {
    "resource_type": "github_workflow",
    "resource_name": "CI",
    "triggers": ["pull_request"],
    "validation_tools_detected": ["terraform validate", "tfsec"],
    "validation_state": "present",
    "runs_on_pull_request": true
  }
}
```

## Fixtures

- `fixtures/should_match/full_validation.yml` — workflow with multiple
  validation tools across `run:` and `uses:` → `validation_state="present"`.
- `fixtures/should_not_match/deploy_only.yml` — deploy workflow with no
  validation steps → `validation_state="absent"` with gap.
