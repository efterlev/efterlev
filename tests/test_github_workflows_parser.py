"""GitHub Actions workflow parser tests (Priority 1.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from efterlev.errors import DetectorError
from efterlev.github_workflows import parse_workflow_file, parse_workflow_tree


def test_parses_basic_workflow(tmp_path: Path) -> None:
    wf = tmp_path / "ci.yml"
    wf.write_text(
        "name: CI\n"
        "on: [pull_request]\n"
        "jobs:\n"
        "  validate:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - run: terraform validate\n"
    )
    parsed = parse_workflow_file(wf)
    assert parsed.name == "CI"
    assert "pull_request" in parsed.on_triggers
    assert "validate" in parsed.jobs
    # The raw body is preserved for detectors that need to reach into it.
    assert parsed.body["jobs"]["validate"]["steps"][0]["run"] == "terraform validate"


def test_workflow_without_name_falls_back_to_filename(tmp_path: Path) -> None:
    wf = tmp_path / "deploy.yml"
    wf.write_text("on: [push]\njobs:\n  deploy:\n    runs-on: ubuntu-latest\n")
    parsed = parse_workflow_file(wf)
    assert parsed.name == "deploy"


def test_on_as_string_normalizes_to_dict(tmp_path: Path) -> None:
    """`on: push` (string form) normalizes to a dict so detectors get a uniform shape."""
    wf = tmp_path / "single.yml"
    wf.write_text("name: x\non: push\njobs: {}\n")
    parsed = parse_workflow_file(wf)
    assert parsed.on_triggers == {"push": {}}


def test_on_as_list_normalizes_to_dict(tmp_path: Path) -> None:
    wf = tmp_path / "multi.yml"
    wf.write_text("name: x\non: [push, pull_request]\njobs: {}\n")
    parsed = parse_workflow_file(wf)
    assert set(parsed.on_triggers.keys()) == {"push", "pull_request"}


def test_on_yaml_quirk_parses_as_bool_true(tmp_path: Path) -> None:
    """PyYAML parses bare `on:` as `True` (the YAML boolean) — the parser
    handles this quirk so workflows that use the unquoted form still parse."""
    wf = tmp_path / "quirk.yml"
    wf.write_text("name: x\non:\n  pull_request:\njobs:\n  noop:\n    runs-on: ubuntu-latest\n")
    parsed = parse_workflow_file(wf)
    # PyYAML parses `on:` as True and the contents become the value of True.
    # Either the normalized "pull_request" key is present or the parser
    # silently emits empty triggers — verify the contents made it through.
    assert "pull_request" in parsed.on_triggers


def test_invalid_yaml_raises_detector_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yml"
    bad.write_text("name: x\nthis is: { not [valid")
    with pytest.raises(DetectorError, match="failed to parse"):
        parse_workflow_file(bad)


def test_non_mapping_top_level_raises(tmp_path: Path) -> None:
    """A workflow file with a list at top level is not a valid workflow."""
    wf = tmp_path / "list.yml"
    wf.write_text("- one\n- two\n")
    with pytest.raises(DetectorError, match="expected a YAML mapping"):
        parse_workflow_file(wf)


# --- tree walker -----------------------------------------------------------


def test_tree_walker_returns_empty_when_no_workflows_dir(tmp_path: Path) -> None:
    """No `.github/workflows/` is the common case for non-Actions repos."""
    result = parse_workflow_tree(tmp_path)
    assert result.workflows == []
    assert result.parse_failures == []


def test_tree_walker_parses_yml_and_yaml_extensions(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\non: [push]\njobs: {}\n")
    (workflows_dir / "deploy.yaml").write_text("name: Deploy\non: [push]\njobs: {}\n")
    # Files outside .github/workflows/ are ignored.
    (tmp_path / "ignore.yml").write_text("name: nope\n")
    # Non-yaml extensions in workflows/ are ignored too.
    (workflows_dir / "README.md").write_text("# notes")

    result = parse_workflow_tree(tmp_path)
    names = {wf.name for wf in result.workflows}
    assert names == {"CI", "Deploy"}


def test_tree_walker_records_paths_relative_to_target(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "ci.yml").write_text("name: CI\non: [push]\njobs: {}\n")

    result = parse_workflow_tree(tmp_path)
    [wf] = result.workflows
    # source_ref.file is repo-relative, no absolute prefix.
    assert str(wf.source_ref.file) == ".github/workflows/ci.yml"
    assert not wf.source_ref.file.is_absolute()


def test_tree_walker_collects_failures_and_continues(tmp_path: Path) -> None:
    """One bad file does not abort the walk — same posture as parse_terraform_tree."""
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "good.yml").write_text("name: good\non: [push]\njobs: {}\n")
    (workflows_dir / "bad.yml").write_text("not: { valid")

    result = parse_workflow_tree(tmp_path)
    assert {wf.name for wf in result.workflows} == {"good"}
    assert len(result.parse_failures) == 1
    assert str(result.parse_failures[0].file) == ".github/workflows/bad.yml"
