"""Tests for `scan_terraform_plan` primitive.

Covers the primitive's orchestration: registry filtering, evidence
aggregation, per-detector summary, and store-record-id tracking. Uses
embedded plan JSON fixtures so Terraform CLI is not a test dependency.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from efterlev.errors import DetectorError
from efterlev.primitives.scan import ScanTerraformPlanInput, scan_terraform_plan
from efterlev.provenance import ProvenanceStore, active_store


def _write_plan(tmp_path: Path, payload: dict, name: str = "plan.json") -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


# Plan JSON with an encrypted and a plaintext S3 bucket declared through
# a for_each-style storage module — exactly the shape that's invisible
# to HCL parsing and the headline motivation for Plan JSON support.
_STORAGE_PLAN = {
    "format_version": "1.2",
    "terraform_version": "1.14.8",
    "planned_values": {
        "root_module": {
            "resources": [],
            "child_modules": [
                {
                    "address": "module.storage",
                    "resources": [
                        {
                            "address": 'module.storage.aws_s3_bucket.this["alpha"]',
                            "mode": "managed",
                            "type": "aws_s3_bucket",
                            "name": "this",
                            "index": "alpha",
                            "values": {"bucket": "app-alpha"},
                        },
                        {
                            "address": 'module.storage.aws_s3_bucket.this["plaintext"]',
                            "mode": "managed",
                            "type": "aws_s3_bucket",
                            "name": "this",
                            "index": "plaintext",
                            "values": {"bucket": "app-plaintext"},
                        },
                        {
                            "address": (
                                "module.storage."
                                "aws_s3_bucket_server_side_encryption_configuration."
                                'this["alpha"]'
                            ),
                            "mode": "managed",
                            "type": "aws_s3_bucket_server_side_encryption_configuration",
                            "name": "this",
                            "index": "alpha",
                            "values": {
                                "rule": [
                                    {
                                        "apply_server_side_encryption_by_default": [
                                            {"sse_algorithm": "AES256"}
                                        ]
                                    }
                                ]
                            },
                        },
                    ],
                }
            ],
        }
    },
    "configuration": {
        "root_module": {"module_calls": {"storage": {"source": "./modules/storage"}}}
    },
}


def test_runs_terraform_detectors_against_plan_resources(tmp_path: Path) -> None:
    plan = _write_plan(tmp_path, _STORAGE_PLAN)
    # No active store — the primitive still returns evidence, just without
    # record-ids (the @detector decorator warns but skips persistence).
    result = scan_terraform_plan(ScanTerraformPlanInput(plan_file=plan))

    # 3 managed resources expected (2 buckets + 1 SSE).
    assert result.resources_parsed == 3
    # Every registered terraform-source detector was iterated (14 at the
    # time of writing — test against get_registry to stay future-proof).
    from efterlev.detectors.base import get_registry

    applicable = {
        s.id for s in get_registry().values() if s.source in ("terraform", "terraform-plan")
    }
    assert result.detectors_run == len(applicable)

    # encryption_s3_at_rest fires on every aws_s3_bucket + SSE resource.
    # Alpha bucket emits "absent" (no inline SSE block in values) AND the
    # SSE resource emits a "present" separate_resource record. Plaintext
    # bucket emits "absent" with no SSE backup — the govnotes-pattern
    # motivation for this whole feature.
    s3_evidence = [ev for ev in result.evidence if ev.detector_id == "aws.encryption_s3_at_rest"]
    states = {
        (ev.content.get("resource_name"), ev.content.get("encryption_state")) for ev in s3_evidence
    }
    assert ("alpha", "absent") in states  # bucket-level inline absent
    assert ("alpha", "present") in states  # separate-resource SSE present
    assert ("plaintext", "absent") in states  # nothing covers plaintext


def test_persists_evidence_to_active_store(tmp_path: Path) -> None:
    plan = _write_plan(tmp_path, _STORAGE_PLAN)
    # The store writes under <workspace>/.efterlev/ — give it a dedicated
    # dir that isn't the plan file's parent.
    workspace = tmp_path / "ws"
    workspace.mkdir()

    with ProvenanceStore(workspace) as store, active_store(store):
        result = scan_terraform_plan(ScanTerraformPlanInput(plan_file=plan))

    assert result.evidence_record_ids  # at least one evidence record id
    assert len(result.evidence_record_ids) == len(result.evidence)


def test_target_root_relativizes_source_refs(tmp_path: Path) -> None:
    # Plan file lives under the workspace; module source exists under it.
    workspace = tmp_path / "repo"
    workspace.mkdir()
    (workspace / "modules" / "storage").mkdir(parents=True)
    plan = _write_plan(workspace, _STORAGE_PLAN)

    result = scan_terraform_plan(ScanTerraformPlanInput(plan_file=plan, target_root=workspace))
    # Every source_ref should be repo-relative (not absolute) per the
    # post-fixup-D contract. The translator may leave absolute paths on
    # candidates outside the repo root, but resources here resolve to
    # "modules/storage" or "plan.json" inside the repo.
    for ev in result.evidence:
        assert not ev.source_ref.file.is_absolute(), ev.source_ref.file


def test_missing_plan_file_raises_detector_error(tmp_path: Path) -> None:
    with pytest.raises(DetectorError, match="plan file not found"):
        scan_terraform_plan(ScanTerraformPlanInput(plan_file=tmp_path / "missing.json"))
