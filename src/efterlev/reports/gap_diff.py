"""Diff between two Gap-Report JSON sidecars.

Priority 2.10a (2026-04-28). Pure-function `compute_gap_diff` takes
two JSON-sidecar dicts (the schema-versioned data emitted by
`render_gap_report_json`) and produces a structured diff: which KSIs
were added, removed, status-changed, or unchanged between two scans.

This module is import-only — no CLI wiring, no HTML rendering. The
follow-up PR (2.10b) will:
  - Add `efterlev report --compare-to <prior>.json` to drive this.
  - Render a `gap-diff-<ts>.html` page from a `GapDiff` instance.

Why a separate module: the diff computation is reusable from the MCP
server (`efterlev_compare_gap`-shaped tool), agent prompts that need
to reason about regression, and the eventual Drift Agent. Keeping it
pure-function with no IO makes that easy.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

GapDiffOutcome = Literal[
    "added",  # KSI in current, not in prior
    "removed",  # KSI in prior, not in current
    "status_changed",  # KSI in both with different status
    "unchanged",  # KSI in both with same status
]


class KsiDiffEntry(BaseModel):
    """One KSI's diff outcome between two scans.

    For `status_changed`, both `prior_status` and `current_status` are
    populated. For `added`, only `current_status`. For `removed`, only
    `prior_status`. For `unchanged`, both are populated and equal.
    """

    model_config = ConfigDict(frozen=True)

    ksi_id: str
    outcome: GapDiffOutcome
    prior_status: str | None = None
    current_status: str | None = None
    # Human-friendly relative-severity label for `status_changed` rows:
    # "improved" (good→better), "regressed" (good→worse), or "shifted"
    # (lateral move, e.g. partial→evidence_layer_inapplicable). Filled
    # only on `status_changed`.
    severity_movement: Literal["improved", "regressed", "shifted"] | None = None


class GapDiff(BaseModel):
    """Diff between two Gap-Report JSON sidecars."""

    model_config = ConfigDict(frozen=True)

    prior_generated_at: str | None = None
    current_generated_at: str | None = None
    prior_baseline_id: str | None = None
    current_baseline_id: str | None = None
    entries: list[KsiDiffEntry] = Field(default_factory=list)

    @property
    def added(self) -> list[KsiDiffEntry]:
        return [e for e in self.entries if e.outcome == "added"]

    @property
    def removed(self) -> list[KsiDiffEntry]:
        return [e for e in self.entries if e.outcome == "removed"]

    @property
    def status_changed(self) -> list[KsiDiffEntry]:
        return [e for e in self.entries if e.outcome == "status_changed"]

    @property
    def unchanged(self) -> list[KsiDiffEntry]:
        return [e for e in self.entries if e.outcome == "unchanged"]

    @property
    def improved(self) -> list[KsiDiffEntry]:
        return [e for e in self.entries if e.severity_movement == "improved"]

    @property
    def regressed(self) -> list[KsiDiffEntry]:
        return [e for e in self.entries if e.severity_movement == "regressed"]


# Severity ranking for the relative-movement label. Lower rank = more
# actionable / "worse" posture. So a rank-increase = improvement.
# `not_applicable` and `evidence_layer_inapplicable` are higher than
# `implemented` because they declare the question is moot rather than
# answered, so a move *from* them *to* implemented is also "improved"
# in coverage terms — but the rank ordering primarily matters for
# distinguishing the actionable {not_implemented, partial} cluster
# from the rest.
_SEVERITY_RANK: dict[str, int] = {
    "not_implemented": 0,
    "partial": 1,
    "implemented": 2,
    "evidence_layer_inapplicable": 3,
    "not_applicable": 4,
}


def compute_gap_diff(prior: dict[str, Any], current: dict[str, Any]) -> GapDiff:
    """Compute a structured diff between two gap-report JSON sidecars.

    Both inputs must be the dict shape `render_gap_report_json` emits
    (schema_version "1.0" or compatible). Validates the report_type is
    "gap" and raises ValueError on mismatch.
    """
    _validate_input(prior, "prior")
    _validate_input(current, "current")

    prior_by_ksi: dict[str, str] = {
        clf["ksi_id"]: clf["status"] for clf in prior.get("ksi_classifications", [])
    }
    current_by_ksi: dict[str, str] = {
        clf["ksi_id"]: clf["status"] for clf in current.get("ksi_classifications", [])
    }

    entries: list[KsiDiffEntry] = []
    all_ksis = sorted(set(prior_by_ksi) | set(current_by_ksi))
    for ksi in all_ksis:
        in_prior = ksi in prior_by_ksi
        in_current = ksi in current_by_ksi
        prior_status = prior_by_ksi.get(ksi)
        current_status = current_by_ksi.get(ksi)

        if in_current and not in_prior:
            outcome: GapDiffOutcome = "added"
            movement = None
        elif in_prior and not in_current:
            outcome = "removed"
            movement = None
        elif prior_status == current_status:
            outcome = "unchanged"
            movement = None
        else:
            outcome = "status_changed"
            movement = _movement_label(prior_status, current_status)

        entries.append(
            KsiDiffEntry(
                ksi_id=ksi,
                outcome=outcome,
                prior_status=prior_status,
                current_status=current_status,
                severity_movement=movement,
            )
        )

    return GapDiff(
        prior_generated_at=prior.get("generated_at"),
        current_generated_at=current.get("generated_at"),
        prior_baseline_id=prior.get("baseline_id"),
        current_baseline_id=current.get("baseline_id"),
        entries=entries,
    )


def _movement_label(
    prior_status: str | None, current_status: str | None
) -> Literal["improved", "regressed", "shifted"]:
    """Classify a status change as improved / regressed / shifted.

    Improved: rank goes up (toward implemented or "moot" buckets).
    Regressed: rank goes down (toward not_implemented).
    Shifted: same rank but different label, OR the rank couldn't be
    resolved (unknown status string from a schema-newer report).
    """
    pr = _SEVERITY_RANK.get(prior_status or "", -1)
    cr = _SEVERITY_RANK.get(current_status or "", -1)
    if pr == -1 or cr == -1:
        return "shifted"
    if cr > pr:
        return "improved"
    if cr < pr:
        return "regressed"
    return "shifted"


def _validate_input(d: dict[str, Any], label: str) -> None:
    """Reject inputs that aren't gap-report sidecars."""
    if not isinstance(d, dict):
        raise ValueError(f"{label}: expected dict, got {type(d).__name__}")
    rt = d.get("report_type")
    if rt is not None and rt != "gap":
        raise ValueError(f"{label}: report_type={rt!r}, expected 'gap'")
