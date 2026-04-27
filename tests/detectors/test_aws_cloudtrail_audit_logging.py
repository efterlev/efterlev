"""Fixture-driven tests for `aws.cloudtrail_audit_logging`."""

from __future__ import annotations

from pathlib import Path

from efterlev.detectors.aws.cloudtrail_audit_logging.detector import detect
from efterlev.terraform import parse_terraform_file

DETECTOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "efterlev"
    / "detectors"
    / "aws"
    / "cloudtrail_audit_logging"
)


def _run(path: Path) -> list:
    return detect(parse_terraform_file(path))


def test_multi_region_trail_emits_present_evidence() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_match" / "multi_region_trail.tf")
    assert len(results) == 1
    ev = results[0]
    # KSI-CMT-LMC added 2026-04-27 (Priority 1.8 cross-map): CloudTrail's
    # AU-2 is in KSI-CMT-LMC's controls array, so the detector legitimately
    # also evidences "Log and monitor modifications to the cloud service offering."
    assert set(ev.ksis_evidenced) == {"KSI-MLA-LET", "KSI-MLA-OSM", "KSI-CMT-LMC"}
    assert set(ev.controls_evidenced) == {"AU-2", "AU-12"}
    assert ev.content["cloudtrail_state"] == "present"
    assert ev.content["is_multi_region"] is True
    assert ev.content["includes_global_events"] is True
    assert ev.content["has_event_selectors"] is True


def test_single_region_trail_emits_partial_evidence() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_not_match" / "single_region_trail.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["cloudtrail_state"] == "partial"
    assert ev.content["is_multi_region"] is False
    # include_global_service_events defaults to true when omitted.
    assert ev.content["includes_global_events"] is True
    assert "is_multi_region_trail" in ev.content["gap"]


def test_no_cloudtrail_emits_nothing() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_not_match" / "no_cloudtrail.tf")
    assert results == []


def test_detector_registered_with_expected_metadata() -> None:
    from efterlev.detectors.base import get_registry

    spec = get_registry()["aws.cloudtrail_audit_logging"]
    assert set(spec.ksis) == {"KSI-MLA-LET", "KSI-MLA-OSM", "KSI-CMT-LMC"}
    assert set(spec.controls) == {"AU-2", "AU-12"}
    assert spec.source == "terraform"
