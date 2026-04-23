"""Fixture-driven tests for `aws.iam_password_policy`."""

from __future__ import annotations

from pathlib import Path

from efterlev.detectors.aws.iam_password_policy.detector import detect
from efterlev.terraform import parse_terraform_file

DETECTOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "efterlev"
    / "detectors"
    / "aws"
    / "iam_password_policy"
)


def _run_detector_on(path: Path) -> list:
    resources = parse_terraform_file(path)
    return detect(resources)


# --- should_match ------------------------------------------------------------


def test_strict_policy_is_sufficient() -> None:
    results = _run_detector_on(DETECTOR_DIR / "fixtures" / "should_match" / "strict_policy.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.detector_id == "aws.iam_password_policy"
    assert ev.ksis_evidenced == []
    assert set(ev.controls_evidenced) == {"IA-5", "IA-5(1)"}
    assert ev.content["posture"] == "sufficient"
    assert ev.content["minimum_password_length"] == 14
    assert ev.content["max_password_age"] == 60
    assert ev.content["password_reuse_prevention"] == 24
    assert all(ev.content["character_requirements"].values())
    assert "gap" not in ev.content


# --- should_not_match --------------------------------------------------------


def test_weak_policy_enumerates_gaps() -> None:
    results = _run_detector_on(DETECTOR_DIR / "fixtures" / "should_not_match" / "weak_policy.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["posture"] == "weak"
    gap = ev.content["gap"]
    # weak_policy.tf violates 5 of 7 thresholds; the detector lists them all.
    assert "minimum_password_length" in gap
    assert "require_numbers" in gap
    assert "require_symbols" in gap
    assert "max_password_age" in gap
    assert "password_reuse_prevention" in gap


def test_no_password_policy_emits_nothing() -> None:
    results = _run_detector_on(DETECTOR_DIR / "fixtures" / "should_not_match" / "no_policy.tf")
    assert results == []


# --- mapping metadata --------------------------------------------------------


def test_detector_registration_reflects_empty_ksis_and_ia_5() -> None:
    from efterlev.detectors.base import get_registry

    spec = get_registry()["aws.iam_password_policy"]
    assert spec.ksis == ()
    assert "IA-5" in spec.controls
    assert "IA-5(1)" in spec.controls
    assert spec.source == "terraform"
