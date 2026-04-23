"""Fixture-driven tests for `aws.cloudtrail_log_file_validation`."""

from __future__ import annotations

from pathlib import Path

from efterlev.detectors.aws.cloudtrail_log_file_validation.detector import detect
from efterlev.terraform import parse_terraform_file

DETECTOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "efterlev"
    / "detectors"
    / "aws"
    / "cloudtrail_log_file_validation"
)


def _run_detector_on(path: Path) -> list:
    resources = parse_terraform_file(path)
    return detect(resources)


# --- should_match ------------------------------------------------------------


def test_validated_trail_emits_enabled() -> None:
    results = _run_detector_on(DETECTOR_DIR / "fixtures" / "should_match" / "validated_trail.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.detector_id == "aws.cloudtrail_log_file_validation"
    assert ev.ksis_evidenced == ["KSI-MLA-OSM"]
    assert ev.controls_evidenced == ["AU-9"]
    assert ev.content["validation_status"] == "enabled"
    assert "gap" not in ev.content


# --- should_not_match --------------------------------------------------------


def test_unvalidated_trail_emits_disabled_with_gap() -> None:
    results = _run_detector_on(
        DETECTOR_DIR / "fixtures" / "should_not_match" / "unvalidated_trail.tf"
    )
    assert len(results) == 1
    ev = results[0]
    assert ev.content["validation_status"] == "disabled"
    assert "gap" in ev.content


def test_no_cloudtrail_resources_emits_nothing() -> None:
    results = _run_detector_on(
        DETECTOR_DIR / "fixtures" / "should_not_match" / "no_cloudtrail_resources.tf"
    )
    assert results == []


# --- mapping metadata --------------------------------------------------------


def test_detector_registration_reflects_mla_osm_and_au_9() -> None:
    from efterlev.detectors.base import get_registry

    spec = get_registry()["aws.cloudtrail_log_file_validation"]
    assert spec.ksis == ("KSI-MLA-OSM",)
    assert spec.controls == ("AU-9",)
    assert spec.source == "terraform"
