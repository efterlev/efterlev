"""Authorization-boundary scoping (Priority 4 of v1-readiness-plan.md).

A FedRAMP customer typically has GovCloud-Terraform in scope and commercial-
Terraform out of scope. Without a way to declare "this directory is in scope;
everything else is out", Efterlev mixes evidence across both, producing a
posture statement that's meaningless to a 3PAO.

This module provides:

- `BoundaryState` — three-valued enum: `in_boundary`, `out_of_boundary`, or
  `boundary_undeclared`. `boundary_undeclared` is the workspace default —
  the customer hasn't told us their scope; we'll show all findings, but
  we can't tell a 3PAO which findings represent the boundary.
- `compute_boundary_state(rel_path, config)` — deterministic helper that
  matches a repo-relative path against the include/exclude patterns from
  `BoundaryConfig`.
- `active_boundary_config(...)` — context manager so `Evidence.create`
  picks up the current workspace boundary at construction time without
  every detector function knowing about boundaries.

Pattern semantics: gitignore-style (gitwildmatch) via `pathspec`. The same
semantics customers expect from `.gitignore`: `boundary/**` matches anything
under `boundary/`, `**/main.tf` matches all `main.tf` files anywhere, etc.

Decision precedence: `exclude` wins. A path that matches both an `include`
and an `exclude` pattern is `out_of_boundary`. Rationale: the customer is
explicit about what to remove from scope, and an explicit exclusion should
not be silently overridden by a broader inclusion.
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import pathspec

if TYPE_CHECKING:
    from efterlev.config import BoundaryConfig

BoundaryState = Literal["in_boundary", "out_of_boundary", "boundary_undeclared"]
"""Three-valued classification:

- `in_boundary` — the file is inside the customer's declared FedRAMP boundary;
  evidence about it should be in the POA&M and the agent's narratives.
- `out_of_boundary` — the file matches an exclude pattern OR doesn't match
  any include pattern (and at least one include pattern was declared).
  Evidence about it surfaces in the HTML report's collapsed section but is
  excluded from the POA&M; agents should not classify against it.
- `boundary_undeclared` — the workspace has no `[boundary]` config, so the
  scope is unknown. The default. Customers should declare scope to get an
  honest posture statement; until they do, evidence flows through everything
  without filtering.
"""


def compute_boundary_state(
    rel_path: Path | str,
    config: BoundaryConfig | None,
) -> BoundaryState:
    """Classify `rel_path` against `config`.

    `rel_path` is a repo-relative path (the same shape `SourceRef.file` uses
    after `parse_terraform_tree`). When `config` is None or both `include`
    and `exclude` are empty, returns `boundary_undeclared`.

    Decision precedence:
    1. If any `exclude` pattern matches → `out_of_boundary` (exclude wins).
    2. Else if `include` is empty → `in_boundary` (no inclusions = everything
       in-scope; an `exclude`-only declaration means "everything except these").
    3. Else if any `include` pattern matches → `in_boundary`.
    4. Else → `out_of_boundary` (an inclusion was declared but didn't match
       this path).
    """
    if config is None or (not config.include and not config.exclude):
        return "boundary_undeclared"

    path_str = str(rel_path).replace("\\", "/")  # normalize for cross-platform consistency

    if config.exclude:
        exclude_spec = pathspec.PathSpec.from_lines("gitwildmatch", config.exclude)
        if exclude_spec.match_file(path_str):
            return "out_of_boundary"

    if not config.include:
        return "in_boundary"

    include_spec = pathspec.PathSpec.from_lines("gitwildmatch", config.include)
    return "in_boundary" if include_spec.match_file(path_str) else "out_of_boundary"


# --- active boundary context (mirrors active_store / current_primitive) ---

_active_boundary_config: contextvars.ContextVar[BoundaryConfig | None] = contextvars.ContextVar(
    "efterlev_active_boundary_config",
    default=None,
)


def get_active_boundary_config() -> BoundaryConfig | None:
    """Return the currently-activated BoundaryConfig, or None.

    Returns None when no boundary has been activated for the current call
    chain. Detectors emitting Evidence consult this; absence means "no
    workspace context, treat as boundary_undeclared."
    """
    return _active_boundary_config.get()


@contextmanager
def active_boundary_config(config: BoundaryConfig | None) -> Iterator[BoundaryConfig | None]:
    """Scope-bind `config` as the active boundary for `Evidence.create`.

    The CLI scan command activates this from the workspace's
    `.efterlev/config.toml` so detectors emit Evidence with the correct
    `boundary_state` without each detector function needing to know about
    boundaries. Tests can also use this directly.

    Passing `config=None` is a no-op activation (useful in test harnesses
    that want to force `boundary_undeclared` regardless of any outer
    activation).
    """
    token = _active_boundary_config.set(config)
    try:
        yield config
    finally:
        _active_boundary_config.reset(token)
