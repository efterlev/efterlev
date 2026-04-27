"""CI validation-gates detector.

Looks at every `.github/workflows/*.yml` workflow and reports whether it
runs validation tooling — `terraform validate`, `terraform plan`,
`tflint`, `tfsec`, `checkov`, etc. — before any deploy step. KSI-CMT-VTD
("Validating Throughout Deployment") asks the customer to demonstrate
automated validation gates in their deployment pipeline; presence of
these tools in CI is the canonical IaC-evidenceable signal.

This is the first detector in the `github-workflows` source category
(Priority 1.2 of v1-readiness-plan.md). It treats each workflow file
as a "resource" and emits one Evidence per file. Workflows without any
validation tool yield Evidence with `validation_state="absent"` and a
gap field — same shape as Terraform detectors that emit per-resource
evidence with finding-state.

KSI mapping per FRMR 0.9.43-beta:
  - KSI-CMT-VTD lists `cm-3` (Configuration Change Control), `cm-3.2`
    (Test, Validate, Document), `cm-4.2` (Verification of Controls
    Implementation), and `si-2` (Flaw Remediation) in its `controls`
    array. The validation-tools-in-CI signal evidences CM-3.2 directly
    (testing/validating changes); CM-3 is the broader change-control
    process which CI-gating partly evidences.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.github_workflows import WorkflowFile
from efterlev.models import Evidence

# Substrings the detector looks for in step `run:` commands. Each is a
# canonical IaC-validation tool customers run in CI. The list is
# deliberately small and biased toward Terraform — that's the codebase
# shape Efterlev primarily covers. Other-tool families (Pulumi `preview`,
# CloudFormation `validate-template`) can be added as detectors land for
# those source categories.
_VALIDATION_TOOLS: tuple[str, ...] = (
    "terraform validate",
    "terraform plan",
    "tflint",
    "tfsec",
    "checkov",
    "trivy config",  # IaC-mode trivy
)


@detector(
    id="github.ci_validation_gates",
    ksis=["KSI-CMT-VTD"],
    controls=["CM-3", "CM-3(2)"],
    source="github-workflows",
    version="0.1.0",
)
def detect(workflows: list[WorkflowFile]) -> list[Evidence]:
    """Emit one Evidence per workflow, characterizing its validation posture.

    Evidences (800-53):  CM-3 (Configuration Change Control — broad),
                         CM-3(2) (Test, Validate, and Document Changes —
                         specific). Both are evidenced when a workflow
                         runs an IaC-validation tool; CM-3 alone when
                         no tool is detected (the workflow exists but
                         doesn't gate validation).
    Evidences (KSI):     KSI-CMT-VTD (Validating Throughout Deployment).
    Does NOT prove:      that the validation step actually fails the
                         build on a finding (some workflows run
                         validation but proceed regardless), that the
                         workflow is wired into branch protection
                         required-checks (separate concern), or that
                         the validation tool's findings are reviewed.
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)

    for wf in workflows:
        out.append(_emit_workflow_evidence(wf, now))

    return out


def _emit_workflow_evidence(wf: WorkflowFile, now: datetime) -> Evidence:
    """Build one Evidence record characterizing a workflow's validation posture."""
    detected_tools = _detect_validation_tools(wf)
    triggers = sorted(wf.on_triggers.keys())

    has_pull_request_trigger = any(t in ("pull_request", "pull_request_target") for t in triggers)

    content: dict[str, Any] = {
        "resource_type": "github_workflow",
        "resource_name": wf.name,
        "triggers": triggers,
        "validation_tools_detected": list(detected_tools),
        "validation_state": "present" if detected_tools else "absent",
        "runs_on_pull_request": has_pull_request_trigger,
    }

    if detected_tools:
        controls = ["CM-3", "CM-3(2)"]
    else:
        controls = ["CM-3"]
        content["gap"] = (
            f"Workflow `{wf.name}` runs but contains no IaC-validation step "
            f"(looked for: {', '.join(_VALIDATION_TOOLS)}). "
            "Validation gating is evidence for KSI-CMT-VTD; without it the "
            "workflow is a deploy pipeline, not a validation pipeline."
        )

    return Evidence.create(
        detector_id="github.ci_validation_gates",
        ksis_evidenced=["KSI-CMT-VTD"],
        controls_evidenced=controls,
        source_ref=wf.source_ref,
        content=content,
        timestamp=now,
    )


def _detect_validation_tools(wf: WorkflowFile) -> list[str]:
    """Walk every job step's `run:` commands looking for known validation tools.

    Returns the (sorted, deduplicated) list of tool substrings found.
    Steps without a `run:` field (uses-based actions like `actions/checkout`)
    are ignored — this detector is concerned with explicit shell-step
    validation, not action-shaped validation. Action-shaped validation
    (e.g. `aquasecurity/tfsec-action`) could be added later via a
    `uses:` substring scan.
    """
    found: set[str] = set()
    for _job_name, job in wf.jobs.items():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            run_cmd = step.get("run")
            if isinstance(run_cmd, str):
                for tool in _VALIDATION_TOOLS:
                    if tool in run_cmd:
                        found.add(tool)
            uses = step.get("uses")
            # Action-shaped validation. Conservative: only count uses-action
            # references whose name looks like a known IaC-validation action.
            # Substring match keeps false positives low while catching common
            # patterns. Each `if` collapses naturally — a uses string can
            # only meaningfully match one of these canonical tool names.
            if isinstance(uses, str):
                if "tfsec" in uses:
                    found.add("tfsec")
                if "checkov" in uses:
                    found.add("checkov")
                if "tflint" in uses:
                    found.add("tflint")
    return sorted(found)
