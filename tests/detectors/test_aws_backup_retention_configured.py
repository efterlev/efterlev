"""Fixture-driven tests for `aws.backup_retention_configured`."""

from __future__ import annotations

from pathlib import Path

from efterlev.detectors.aws.backup_retention_configured.detector import detect
from efterlev.terraform import parse_terraform_file

DETECTOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "efterlev"
    / "detectors"
    / "aws"
    / "backup_retention_configured"
)


def _run(path: Path) -> list:
    return detect(parse_terraform_file(path))


def test_rds_with_retention_emits_present_evidence() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_match" / "rds_with_retention.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.ksis_evidenced == ["KSI-RPL-ABO"]
    assert ev.controls_evidenced == ["CP-9"]
    assert ev.content["mechanism"] == "rds_retention"
    assert ev.content["backup_state"] == "present"
    assert ev.content["retention_days"] == 7


def test_s3_versioning_enabled_emits_present_evidence() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_match" / "s3_versioning_enabled.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["mechanism"] == "s3_versioning"
    assert ev.content["backup_state"] == "present"
    assert ev.content["versioning_status"] == "Enabled"


def test_rds_without_retention_emits_absent_evidence() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_not_match" / "rds_no_retention.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["backup_state"] == "absent"
    assert ev.content["retention_days"] == 0
    assert "gap" in ev.content


def test_s3_versioning_suspended_emits_absent_evidence() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_not_match" / "s3_versioning_suspended.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["backup_state"] == "absent"
    assert ev.content["versioning_status"] == "Suspended"
    assert "gap" in ev.content


def test_detector_registered_with_expected_metadata() -> None:
    from efterlev.detectors.base import get_registry

    spec = get_registry()["aws.backup_retention_configured"]
    assert spec.ksis == ("KSI-RPL-ABO",)
    assert spec.controls == ("CP-9",)
    assert spec.source == "terraform"
