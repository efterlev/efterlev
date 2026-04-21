"""Fixture-driven tests for `aws.tls_on_lb_listeners`."""

from __future__ import annotations

from pathlib import Path

from efterlev.detectors.aws.tls_on_lb_listeners.detector import detect
from efterlev.terraform import parse_terraform_file

DETECTOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "efterlev"
    / "detectors"
    / "aws"
    / "tls_on_lb_listeners"
)


def _run(path: Path) -> list:
    return detect(parse_terraform_file(path))


def test_https_listener_emits_present_evidence() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_match" / "https_listener.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.detector_id == "aws.tls_on_lb_listeners"
    assert ev.ksis_evidenced == ["KSI-SVC-SNT"]
    assert ev.controls_evidenced == ["SC-8"]
    assert ev.content["resource_type"] == "aws_lb_listener"
    assert ev.content["protocol"] == "HTTPS"
    assert ev.content["tls_state"] == "present"
    assert ev.content["ssl_policy"] == "ELBSecurityPolicy-TLS13-1-2-2021-06"
    assert ev.content["certificate_arn_present"] is True


def test_http_listener_emits_absent_evidence_with_gap_string() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_not_match" / "http_listener.tf")
    assert len(results) == 1
    ev = results[0]
    assert ev.content["protocol"] == "HTTP"
    assert ev.content["tls_state"] == "absent"
    assert "gap" in ev.content


def test_no_listener_resources_emits_nothing() -> None:
    results = _run(DETECTOR_DIR / "fixtures" / "should_not_match" / "no_listener_resources.tf")
    assert results == []


def test_detector_registered_with_expected_metadata() -> None:
    from efterlev.detectors.base import get_registry

    spec = get_registry()["aws.tls_on_lb_listeners"]
    assert spec.ksis == ("KSI-SVC-SNT",)
    assert spec.controls == ("SC-8",)
    assert spec.source == "terraform"
