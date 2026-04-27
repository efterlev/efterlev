"""Parse GitHub Actions workflows under `.github/workflows/`.

Strategy: PyYAML-loads each `.yml`/`.yaml` file and constructs a typed
`WorkflowFile` model preserving the fields detectors care about: name,
on-triggers, jobs, and the raw body for cases where a detector wants to
do its own structural lookup.

Collect-and-continue: a malformed YAML file is recorded as a parse
failure rather than aborting the walk — same posture as
`parse_terraform_tree`. Real-world repos sometimes contain malformed or
templated workflows; one bad file shouldn't block detection on the rest.

Scope: v1.2 reads `.github/workflows/*.yml` and `.github/workflows/*.yaml`
only. GitLab-CI, Jenkinsfiles, CircleCI, and reusable-workflow inputs are
out of scope; if they become customer-relevant they'd be additional source
categories on the same model.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from efterlev.errors import DetectorError
from efterlev.models import SourceRef


class WorkflowFile(BaseModel):
    """One parsed GitHub Actions workflow file.

    Field semantics mirror the GitHub Actions schema:
    - `name` — the `name:` field if set; falls back to filename when absent
    - `on_triggers` — the raw `on:` block (event triggers + filters);
      keys vary by event type so we keep it as `dict[str, Any]`
    - `jobs` — the raw `jobs:` block, dict of job-name → job-definition
    - `body` — the entire raw parsed YAML for detectors that need to look
      at fields outside the typed structure
    - `source_ref` — repo-relative path with no line number (workflow
      files are conceptually one logical unit; line-level evidence inside
      a workflow can be added later if a detector needs it)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    on_triggers: dict[str, Any] = Field(default_factory=dict)
    jobs: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] = Field(default_factory=dict)
    source_ref: SourceRef


@dataclass(frozen=True)
class WorkflowParseFailure:
    """One workflow file the parser couldn't read."""

    file: Path
    """Repo-relative path."""
    reason: str
    """Short error message — typically `yaml.YAMLError` class + str(e)."""


@dataclass(frozen=True)
class WorkflowParseResult:
    """What `parse_workflow_tree` returns: parsed workflows + per-file failures.

    Mirrors `TerraformParseResult` for symmetry. Detectors operate on
    `workflows`; the scan layer surfaces `parse_failures` as warnings.
    """

    workflows: list[WorkflowFile]
    parse_failures: list[WorkflowParseFailure]

    @property
    def files_failed(self) -> int:
        return len(self.parse_failures)


def parse_workflow_tree(target_dir: Path) -> WorkflowParseResult:
    """Walk `.github/workflows/` under `target_dir` and parse every workflow file.

    `.github/workflows/` is the canonical location GitHub Actions reads
    from; any `.yml` or `.yaml` file there is a workflow. Files outside
    this directory are ignored — the convention is fixed by GitHub Actions
    itself, not customizable per-repo.

    Returns an empty result (no failures, no workflows) when
    `.github/workflows/` does not exist. That's the common case for repos
    without GitHub Actions; detectors with `source="github-workflows"`
    just emit nothing for that codebase.
    """
    workflow_dir = target_dir / ".github" / "workflows"
    if not workflow_dir.is_dir():
        return WorkflowParseResult(workflows=[], parse_failures=[])

    workflows: list[WorkflowFile] = []
    parse_failures: list[WorkflowParseFailure] = []
    for wf_file in sorted(workflow_dir.iterdir()):
        if wf_file.suffix not in (".yml", ".yaml"):
            continue
        relative = wf_file.relative_to(target_dir)
        try:
            workflows.append(parse_workflow_file(wf_file, record_as=relative))
        except DetectorError as e:
            reason = str(e).replace(f"failed to parse {wf_file}: ", "")
            parse_failures.append(WorkflowParseFailure(file=relative, reason=reason))
    return WorkflowParseResult(workflows=workflows, parse_failures=parse_failures)


def parse_workflow_file(path: Path, *, record_as: Path | None = None) -> WorkflowFile:
    """Parse one workflow file; return a typed `WorkflowFile`.

    `record_as` overrides the path stored in `source_ref.file` — typically
    the repo-relative path produced by `parse_workflow_tree`. When None,
    `path` is recorded verbatim.
    """
    recorded = record_as if record_as is not None else path
    text = path.read_text(encoding="utf-8")
    try:
        body = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise DetectorError(f"failed to parse {path}: {type(e).__name__}: {e}") from e

    if not isinstance(body, dict):
        # An empty file or a non-mapping top-level (e.g. just a list) is not
        # a valid workflow. Surface as a parse failure so callers can flag
        # rather than silently emitting an unusable WorkflowFile.
        raise DetectorError(
            f"failed to parse {path}: expected a YAML mapping at top level, "
            f"got {type(body).__name__}"
        )

    # PyYAML 1.1 quirk: bare `on:` parses as the YAML boolean `True`. Coerce
    # any non-string keys to string so the resulting `body` dict has a
    # uniform type (Pydantic `dict[str, Any]` rejects bool keys). The True
    # key carries `on:` content; rewrite to "on" to match user expectation.
    body = {
        ("on" if k is True else str(k) if not isinstance(k, str) else k): v for k, v in body.items()
    }

    # `on:` is sometimes a string (`on: push`), sometimes a list, sometimes
    # a dict. Normalize to dict for typed access; preserve the raw form in
    # `body` for detectors that need it.
    on_raw = body.get("on", {})
    on_triggers: dict[str, Any]
    if isinstance(on_raw, dict):
        on_triggers = dict(on_raw)
    elif isinstance(on_raw, list):
        on_triggers = {trigger: {} for trigger in on_raw if isinstance(trigger, str)}
    elif isinstance(on_raw, str):
        on_triggers = {on_raw: {}}
    else:
        on_triggers = {}

    jobs_raw = body.get("jobs", {})
    jobs = jobs_raw if isinstance(jobs_raw, dict) else {}

    name_raw = body.get("name")
    name = name_raw if isinstance(name_raw, str) and name_raw else path.stem

    return WorkflowFile(
        name=name,
        on_triggers=on_triggers,
        jobs=jobs,
        body=body,
        source_ref=SourceRef(file=recorded),
    )
