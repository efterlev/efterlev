"""Fixture-driven tests for `aws.encryption_s3_at_rest`.

Loads each `.tf` file in the detector's `fixtures/{should_match,should_not_match}/`
directories, parses it via the Terraform parser, runs the detector, and
asserts on the emitted Evidence shape and count. The `should_match` /
`should_not_match` split is the CONTRIBUTING.md-blessed contract for
community contributors adding new detectors.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from efterlev.detectors.aws.encryption_s3_at_rest.detector import detect
from efterlev.terraform import parse_terraform_file

DETECTOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "efterlev"
    / "detectors"
    / "aws"
    / "encryption_s3_at_rest"
)


@pytest.fixture(autouse=True)
def _clean_detector_registry() -> None:
    """Prevent stale registry entries bleeding across tests.

    The decorator registers on import; re-importing after clear_registry
    is not trivial, so we import the detector module at top-of-file and
    trust its registration is set for this test session. This fixture
    exists mainly to make test order independent for any peer tests that
    also register detectors.
    """


def _run_detector_on(path: Path) -> list:
    resources = parse_terraform_file(path)
    return detect(resources)


# --- should_match -------------------------------------------------------------


def test_inline_kms_bucket_emits_present_evidence() -> None:
    results = _run_detector_on(DETECTOR_DIR / "fixtures" / "should_match" / "inline_kms.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.detector_id == "aws.encryption_s3_at_rest"
    assert ev.ksis_evidenced == []
    assert set(ev.controls_evidenced) == {"SC-28", "SC-28(1)"}
    assert ev.content["resource_type"] == "aws_s3_bucket"
    assert ev.content["resource_name"] == "audit_logs"
    assert ev.content["encryption_state"] == "present"
    assert ev.content["location"] == "inline"
    assert ev.content["algorithm"] == "aws:kms"


def test_inline_aes256_bucket_emits_present_evidence() -> None:
    results = _run_detector_on(DETECTOR_DIR / "fixtures" / "should_match" / "inline_aes256.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["encryption_state"] == "present"
    assert ev.content["algorithm"] == "AES256"
    assert set(ev.controls_evidenced) == {"SC-28", "SC-28(1)"}


def test_separate_sse_resource_emits_two_evidence_records() -> None:
    # One for the bucket itself (absent inline SSE) and one for the separate
    # aws_s3_bucket_server_side_encryption_configuration resource. The Gap
    # Agent cross-references; v0 emits both facts.
    results = _run_detector_on(
        DETECTOR_DIR / "fixtures" / "should_match" / "separate_sse_resource.tf"
    )
    assert len(results) == 2
    by_rtype = {ev.content["resource_type"]: ev for ev in results}

    bucket_ev = by_rtype["aws_s3_bucket"]
    assert bucket_ev.content["encryption_state"] == "absent"
    assert bucket_ev.content.get("gap")

    sse_ev = by_rtype["aws_s3_bucket_server_side_encryption_configuration"]
    assert sse_ev.content["encryption_state"] == "present"
    assert sse_ev.content["location"] == "separate_resource"
    assert sse_ev.content["algorithm"] == "aws:kms"


# --- should_not_match ---------------------------------------------------------


def test_plain_bucket_emits_absent_evidence_with_gap_string() -> None:
    results = _run_detector_on(DETECTOR_DIR / "fixtures" / "should_not_match" / "plain_bucket.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["encryption_state"] == "absent"
    assert ev.content["resource_name"] == "public_assets"
    assert ev.controls_evidenced == ["SC-28"]  # no enhancement when absent
    assert "gap" in ev.content


def test_no_s3_resources_emits_nothing() -> None:
    results = _run_detector_on(
        DETECTOR_DIR / "fixtures" / "should_not_match" / "no_s3_resources.tf"
    )
    assert results == []


# --- mapping metadata --------------------------------------------------------


def test_detector_registration_reflects_ksis_empty_and_sc_28_controls() -> None:
    # Cross-check the @detector arguments via the registry (don't hard-code
    # expectations in multiple places — the source of truth is the decorator).
    from efterlev.detectors.base import get_registry

    spec = get_registry()["aws.encryption_s3_at_rest"]
    assert spec.ksis == ()  # empty, per DECISIONS 2026-04-21
    assert "SC-28" in spec.controls
    assert "SC-28(1)" in spec.controls
    assert spec.source == "terraform"
