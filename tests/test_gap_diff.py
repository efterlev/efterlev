"""Tests for `compute_gap_diff` — pure-function diff between two gap-report
JSON sidecars.

Priority 2.10a (2026-04-28). The HTML diff page + CLI command land in
the follow-up PR; this PR ships the diff *computation* with full unit
coverage so the renderer/CLI can plug in confidently.
"""

from __future__ import annotations

import pytest

from efterlev.reports import GapDiff, KsiDiffEntry, compute_gap_diff


def _sidecar(
    *,
    classifications: list[tuple[str, str]] | None = None,
    generated_at: str = "2026-04-28T12:00:00+00:00",
    baseline_id: str = "fedramp-20x-moderate",
) -> dict:
    """Build a minimal gap-report-shaped sidecar dict."""
    return {
        "schema_version": "1.0",
        "report_type": "gap",
        "generated_at": generated_at,
        "baseline_id": baseline_id,
        "frmr_version": "0.9.43-beta",
        "workspace_boundary_state": "boundary_undeclared",
        "ksi_classifications": [
            {
                "ksi_id": ksi,
                "status": status,
                "rationale": "...",
                "evidence_ids": [],
                "boundary_state": "boundary_undeclared",
            }
            for ksi, status in (classifications or [])
        ],
        "unmapped_findings": [],
        "claim_record_ids": [],
        "coverage_matrix": None,
    }


# --- top-level shape -------------------------------------------------------


def test_compute_returns_gap_diff() -> None:
    diff = compute_gap_diff(_sidecar(), _sidecar())
    assert isinstance(diff, GapDiff)
    assert diff.entries == []


def test_metadata_propagated_from_inputs() -> None:
    prior = _sidecar(generated_at="2026-04-20T08:00:00+00:00", baseline_id="prior-baseline")
    current = _sidecar(generated_at="2026-04-28T12:00:00+00:00", baseline_id="curr-baseline")
    diff = compute_gap_diff(prior, current)
    assert diff.prior_generated_at == "2026-04-20T08:00:00+00:00"
    assert diff.current_generated_at == "2026-04-28T12:00:00+00:00"
    assert diff.prior_baseline_id == "prior-baseline"
    assert diff.current_baseline_id == "curr-baseline"


# --- outcome categories ---------------------------------------------------


def test_added_ksi() -> None:
    """KSI in current but not prior."""
    prior = _sidecar(classifications=[])
    current = _sidecar(classifications=[("KSI-SVC-SNT", "implemented")])
    diff = compute_gap_diff(prior, current)
    assert len(diff.added) == 1
    e = diff.added[0]
    assert e.ksi_id == "KSI-SVC-SNT"
    assert e.outcome == "added"
    assert e.prior_status is None
    assert e.current_status == "implemented"
    assert e.severity_movement is None


def test_removed_ksi() -> None:
    """KSI in prior but not current."""
    prior = _sidecar(classifications=[("KSI-IAM-MFA", "partial")])
    current = _sidecar(classifications=[])
    diff = compute_gap_diff(prior, current)
    assert len(diff.removed) == 1
    e = diff.removed[0]
    assert e.outcome == "removed"
    assert e.prior_status == "partial"
    assert e.current_status is None


def test_unchanged_ksi() -> None:
    prior = _sidecar(classifications=[("KSI-SVC-SNT", "implemented")])
    current = _sidecar(classifications=[("KSI-SVC-SNT", "implemented")])
    diff = compute_gap_diff(prior, current)
    assert len(diff.unchanged) == 1
    assert diff.unchanged[0].outcome == "unchanged"
    assert diff.unchanged[0].severity_movement is None


def test_status_changed_ksi() -> None:
    prior = _sidecar(classifications=[("KSI-SVC-SNT", "partial")])
    current = _sidecar(classifications=[("KSI-SVC-SNT", "implemented")])
    diff = compute_gap_diff(prior, current)
    assert len(diff.status_changed) == 1
    e = diff.status_changed[0]
    assert e.outcome == "status_changed"
    assert e.prior_status == "partial"
    assert e.current_status == "implemented"
    assert e.severity_movement == "improved"


# --- severity_movement classification --------------------------------------


def test_movement_improved_when_status_rank_increases() -> None:
    """not_implemented → partial = improved (less actionable)."""
    diff = compute_gap_diff(
        _sidecar(classifications=[("KSI-X", "not_implemented")]),
        _sidecar(classifications=[("KSI-X", "partial")]),
    )
    assert diff.status_changed[0].severity_movement == "improved"
    assert len(diff.improved) == 1


def test_movement_regressed_when_status_rank_decreases() -> None:
    """implemented → partial = regressed."""
    diff = compute_gap_diff(
        _sidecar(classifications=[("KSI-X", "implemented")]),
        _sidecar(classifications=[("KSI-X", "partial")]),
    )
    assert diff.status_changed[0].severity_movement == "regressed"
    assert len(diff.regressed) == 1


def test_movement_improved_into_inapplicable() -> None:
    """not_implemented → evidence_layer_inapplicable = improved (the KSI
    is now declared moot, which is a coverage improvement vs the prior
    actionable state)."""
    diff = compute_gap_diff(
        _sidecar(classifications=[("KSI-X", "not_implemented")]),
        _sidecar(classifications=[("KSI-X", "evidence_layer_inapplicable")]),
    )
    assert diff.status_changed[0].severity_movement == "improved"


def test_movement_shifted_for_unknown_status() -> None:
    """A status string the ranking map doesn't know lands as 'shifted'
    (e.g., a future schema with a new status)."""
    diff = compute_gap_diff(
        _sidecar(classifications=[("KSI-X", "implemented")]),
        _sidecar(classifications=[("KSI-X", "future_status_value")]),
    )
    assert diff.status_changed[0].severity_movement == "shifted"


# --- multi-KSI mixed cases -------------------------------------------------


def test_mixed_diff_categorizes_each_ksi() -> None:
    prior = _sidecar(
        classifications=[
            ("KSI-A", "not_implemented"),  # → resolved (added implemented)
            ("KSI-B", "implemented"),  # → unchanged
            ("KSI-C", "implemented"),  # → regressed (now partial)
            ("KSI-D", "partial"),  # → removed
        ]
    )
    current = _sidecar(
        classifications=[
            ("KSI-A", "implemented"),
            ("KSI-B", "implemented"),
            ("KSI-C", "partial"),
            ("KSI-E", "not_implemented"),  # → added
        ]
    )
    diff = compute_gap_diff(prior, current)
    by_id = {e.ksi_id: e for e in diff.entries}
    assert by_id["KSI-A"].outcome == "status_changed"
    assert by_id["KSI-A"].severity_movement == "improved"
    assert by_id["KSI-B"].outcome == "unchanged"
    assert by_id["KSI-C"].outcome == "status_changed"
    assert by_id["KSI-C"].severity_movement == "regressed"
    assert by_id["KSI-D"].outcome == "removed"
    assert by_id["KSI-E"].outcome == "added"

    # Properties match the entry counts.
    assert len(diff.added) == 1
    assert len(diff.removed) == 1
    assert len(diff.unchanged) == 1
    assert len(diff.status_changed) == 2
    assert len(diff.improved) == 1
    assert len(diff.regressed) == 1


def test_entries_sorted_alphabetically_by_ksi_id() -> None:
    diff = compute_gap_diff(
        _sidecar(classifications=[("KSI-Z-FIRST", "implemented"), ("KSI-A-SECOND", "partial")]),
        _sidecar(classifications=[("KSI-Z-FIRST", "implemented"), ("KSI-A-SECOND", "partial")]),
    )
    assert [e.ksi_id for e in diff.entries] == ["KSI-A-SECOND", "KSI-Z-FIRST"]


# --- input validation -----------------------------------------------------


def test_rejects_non_dict_input() -> None:
    with pytest.raises(ValueError, match="expected dict"):
        compute_gap_diff("not a dict", _sidecar())  # type: ignore[arg-type]


def test_rejects_wrong_report_type() -> None:
    """Refuse to diff a documentation-report sidecar against a gap-report."""
    bad = _sidecar()
    bad["report_type"] = "documentation"
    with pytest.raises(ValueError, match="report_type='documentation', expected 'gap'"):
        compute_gap_diff(bad, _sidecar())


def test_accepts_input_without_report_type_field() -> None:
    """Older sidecars without report_type are accepted (forward-compat for
    the legacy schema before priority 2.1 added the field)."""
    minimal = {
        "schema_version": "0.9",
        "ksi_classifications": [{"ksi_id": "KSI-X", "status": "partial"}],
    }
    diff = compute_gap_diff(minimal, _sidecar())
    assert len(diff.entries) == 1


# --- KsiDiffEntry typed model ---------------------------------------------


def test_ksi_diff_entry_is_frozen() -> None:
    """The diff result is a frozen Pydantic model — entries can't be
    mutated by callers (matches the rest of the gap-report codebase)."""
    from pydantic import ValidationError

    entry = KsiDiffEntry(
        ksi_id="KSI-X",
        outcome="added",
        current_status="implemented",
    )
    with pytest.raises(ValidationError):
        entry.ksi_id = "different"  # type: ignore[misc]
