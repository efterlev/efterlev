"""Fixture-driven tests for `aws.mfa_required_on_iam_policies`."""

from __future__ import annotations

from pathlib import Path

from efterlev.detectors.aws.mfa_required_on_iam_policies.detector import detect
from efterlev.terraform import parse_terraform_file

DETECTOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "efterlev"
    / "detectors"
    / "aws"
    / "mfa_required_on_iam_policies"
)


def _run(path: Path) -> list:
    return detect(parse_terraform_file(path))


def test_mfa_gated_policy_emits_present_evidence() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_match" / "mfa_gated_policy.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.ksis_evidenced == ["KSI-IAM-MFA"]
    assert ev.controls_evidenced == ["IA-2"]
    assert ev.content["mfa_required"] == "present"
    assert ev.content["allow_statement_count"] == 1


def test_policy_without_mfa_emits_absent_evidence() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_not_match" / "no_mfa_policy.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["mfa_required"] == "absent"
    assert ev.content["allow_statement_count"] == 1
    assert "gap" in ev.content


def test_jsonencode_policy_is_unparseable() -> None:
    # `jsonencode(...)` renders as `"${jsonencode(...)}"` in python-hcl2; we
    # cannot statically resolve it. Detector emits mfa_required="unparseable"
    # and the Gap Agent treats that as partial rather than false-positive.
    results = _run(DETECTOR_DIR / "fixtures" / "should_not_match" / "jsonencode_policy.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["mfa_required"] == "unparseable"
    assert "gap" in ev.content


def test_no_iam_resources_emits_nothing() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_not_match" / "no_iam_resources.tf")
    assert results == []


def test_detector_registered_with_expected_metadata() -> None:
    from efterlev.detectors.base import get_registry

    spec = get_registry()["aws.mfa_required_on_iam_policies"]
    assert spec.ksis == ("KSI-IAM-MFA",)
    assert spec.controls == ("IA-2",)
    assert spec.source == "terraform"
