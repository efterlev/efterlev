"""Fixture-driven tests for `github.ci_validation_gates`."""

from __future__ import annotations

from pathlib import Path

from efterlev.detectors.github.ci_validation_gates.detector import detect
from efterlev.github_workflows import parse_workflow_file

DETECTOR_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "efterlev"
    / "detectors"
    / "github"
    / "ci_validation_gates"
)


def _run_detector_on(path: Path) -> list:
    workflow = parse_workflow_file(path)
    return detect([workflow])


# --- should_match ----------------------------------------------------------


def test_full_validation_workflow_emits_present_with_tools() -> None:
    """The canonical evidence shape: a workflow that runs validation in CI,
    triggered on PR. Evidences both CM-3 and CM-3(2)."""
    results = _run_detector_on(DETECTOR_DIR / "fixtures" / "should_match" / "full_validation.yml")
    assert len(results) == 1
    ev = results[0]
    assert ev.detector_id == "github.ci_validation_gates"
    assert ev.ksis_evidenced == ["KSI-CMT-VTD"]
    assert set(ev.controls_evidenced) == {"CM-3", "CM-3(2)"}
    content = ev.content
    assert content["resource_type"] == "github_workflow"
    assert content["resource_name"] == "CI"
    assert content["validation_state"] == "present"
    assert content["runs_on_pull_request"] is True
    # The fixture has terraform validate, terraform plan, tfsec, checkov.
    tools = set(content["validation_tools_detected"])
    assert "terraform validate" in tools
    assert "terraform plan" in tools
    assert "tfsec" in tools
    assert "checkov" in tools
    assert "gap" not in content


# --- should_not_match ------------------------------------------------------


def test_deploy_only_workflow_emits_absent_with_gap() -> None:
    """A deploy-only workflow runs `terraform apply` but no validation —
    evidences CM-3 (the workflow exists) but not CM-3(2). Gap field is
    populated."""
    results = _run_detector_on(DETECTOR_DIR / "fixtures" / "should_not_match" / "deploy_only.yml")
    assert len(results) == 1
    ev = results[0]
    content = ev.content
    assert content["validation_state"] == "absent"
    assert content["validation_tools_detected"] == []
    assert ev.controls_evidenced == ["CM-3"]
    assert "no IaC-validation step" in content["gap"]
    # `runs_on_pull_request` is False — this workflow only triggers on push.
    assert content["runs_on_pull_request"] is False


def test_no_workflows_emits_nothing() -> None:
    """An empty workflow list yields no evidence — silence is fine, the Gap
    Agent classifies KSI-CMT-VTD as `not_implemented` if appropriate."""
    assert detect([]) == []


# --- mapping metadata ------------------------------------------------------


def test_detector_registration_metadata() -> None:
    from efterlev.detectors.base import get_registry

    spec = get_registry()["github.ci_validation_gates"]
    assert spec.ksis == ("KSI-CMT-VTD",)
    assert "CM-3" in spec.controls
    assert "CM-3(2)" in spec.controls
    assert spec.source == "github-workflows"
