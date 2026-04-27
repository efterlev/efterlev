"""`scan_github_workflows` primitive — parse `.github/workflows/`, run detectors.

Mirrors `scan_terraform`'s structure. Reads workflow files via
`parse_workflow_tree`, dispatches to every detector with
`source="github-workflows"`, returns a `ScanGithubWorkflowsOutput`.

Priority 1.2 (2026-04-27): the new repo-metadata source category that
unlocks the CMT theme (Change Management Throughput) — KSIs about CI/CD
posture that have no analog in IaC alone (CMT-VTD: Validating Throughout
Deployment, CMT-RMV: Redeploying vs Modifying, CMT-LMC: Logging Changes
to the cloud service offering).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

import efterlev.detectors  # noqa: F401 — triggers detector registrations
from efterlev.detectors.base import Source, get_registry
from efterlev.github_workflows import parse_workflow_tree
from efterlev.models import Evidence
from efterlev.primitives.base import primitive
from efterlev.primitives.scan.scan_terraform import DetectorRunSummary, ParseFailureRecord
from efterlev.provenance.context import get_active_store


class ScanGithubWorkflowsInput(BaseModel):
    """Input to `scan_github_workflows`."""

    model_config = ConfigDict(frozen=True)

    target_dir: Path


class ScanGithubWorkflowsOutput(BaseModel):
    """Structured summary of a github-workflows scan.

    Reuses `DetectorRunSummary` and `ParseFailureRecord` from
    `scan_terraform.py` — the shapes are identical and live in one
    place to keep the scan-summary CSS/template logic uniform across
    sources.
    """

    model_config = ConfigDict(frozen=True)

    workflows_parsed: int
    detectors_run: int
    evidence: list[Evidence] = Field(default_factory=list)
    evidence_record_ids: list[str] = Field(default_factory=list)
    per_detector: list[DetectorRunSummary] = Field(default_factory=list)
    parse_failures: list[ParseFailureRecord] = Field(default_factory=list)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def files_failed(self) -> int:
        return len(self.parse_failures)


@primitive(capability="scan", side_effects=False, version="0.1.0", deterministic=True)
def scan_github_workflows(input: ScanGithubWorkflowsInput) -> ScanGithubWorkflowsOutput:
    """Parse `.github/workflows/` under `target_dir` and run every github-workflows detector.

    When the target has no `.github/workflows/` directory (typical for
    repos without GitHub Actions), this returns an empty result —
    detectors emit nothing, no error. The CLI scan command runs both
    `scan_terraform` and `scan_github_workflows`; an empty result from
    one doesn't affect the other.
    """
    parse_result = parse_workflow_tree(input.target_dir)
    workflows = parse_result.workflows
    workflow_source: Source = "github-workflows"
    workflow_detectors = [
        spec for spec in get_registry().values() if spec.source == workflow_source
    ]

    store = get_active_store()
    pre_ids: set[str] = set(store.iter_records()) if store is not None else set()

    evidence: list[Evidence] = []
    per_detector: list[DetectorRunSummary] = []
    for spec in workflow_detectors:
        produced = spec.callable(workflows)
        evidence.extend(produced)
        per_detector.append(
            DetectorRunSummary(
                detector_id=spec.id,
                version=spec.version,
                evidence_count=len(produced),
            )
        )

    evidence_record_ids: list[str] = []
    if store is not None:
        for rid in store.iter_records():
            if rid not in pre_ids:
                evidence_record_ids.append(rid)

    return ScanGithubWorkflowsOutput(
        workflows_parsed=len(workflows),
        detectors_run=len(workflow_detectors),
        evidence=evidence,
        evidence_record_ids=evidence_record_ids,
        per_detector=per_detector,
        parse_failures=[
            ParseFailureRecord(file=f.file, reason=f.reason) for f in parse_result.parse_failures
        ],
    )
