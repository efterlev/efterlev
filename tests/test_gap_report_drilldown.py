"""Tests for the per-classification drill-down to source refs.

Priority 2.9 (2026-04-28). Each classification card now exposes a
collapsed `<details>` listing the cited evidence's
`detector_id` + `source_file:line_range`, so reviewers can drill down
from a classification to the actual scanner output without leaving
the report. The JSON sidecar gains a parallel `cited_evidence_refs`
field per classification.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from efterlev.agents import GapReport
from efterlev.agents.gap import KsiClassification
from efterlev.models import Evidence, SourceRef
from efterlev.reports import render_gap_report_html, render_gap_report_json


def _ev(
    *,
    detector_id: str = "aws.tls_on_lb_listeners",
    file: str = "main.tf",
    line_start: int | None = 12,
    line_end: int | None = 24,
) -> Evidence:
    """Build an Evidence with a deterministic id (hex-shaped)."""
    return Evidence(
        evidence_id="sha256:" + ("a" * 64),
        detector_id=detector_id,
        ksis_evidenced=["KSI-SVC-SNT"],
        controls_evidenced=["SC-8"],
        source_ref=SourceRef(file=Path(file), line_start=line_start, line_end=line_end),
        content={"resource_type": "aws_lb_listener"},
        timestamp=datetime(2026, 4, 28, 12, 0, 0, tzinfo=UTC),
        boundary_state="boundary_undeclared",
    )


def _classification(
    ksi_id: str = "KSI-SVC-SNT",
    status: str = "partial",
    evidence_ids: list[str] | None = None,
) -> KsiClassification:
    return KsiClassification(
        ksi_id=ksi_id,
        status=status,  # type: ignore[arg-type]
        rationale="...",
        evidence_ids=evidence_ids or ["sha256:" + ("a" * 64)],
    )


def _report(*classifications: KsiClassification) -> GapReport:
    return GapReport(
        ksi_classifications=list(classifications),
        unmapped_findings=[],
        claim_record_ids=[],
    )


def _kwargs() -> dict:
    return {
        "baseline_id": "fedramp-20x-moderate",
        "frmr_version": "0.9.43-beta",
        "generated_at": datetime(2026, 4, 28, 12, 0, 0, tzinfo=UTC),
    }


# --- HTML drill-down section -----------------------------------------------


def test_drilldown_details_renders_when_evidence_resolves() -> None:
    """When the renderer can match a cited evidence_id to an Evidence
    record (passed via `evidence=` kwarg), the classification card emits
    a `<details class="evidence-drilldown">` block listing detector_id
    and source_file:line_range."""
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        evidence=[_ev()],
        **_kwargs(),
    )
    assert '<details class="evidence-drilldown">' in html
    assert "<summary>Show cited source refs (1)</summary>" in html
    assert "main.tf" in html
    assert "12-24" in html
    assert "aws.tls_on_lb_listeners" in html


def test_drilldown_omitted_when_no_matching_evidence() -> None:
    """If the renderer doesn't have an Evidence record for any cited
    evidence_id, the drill-down section is omitted (nothing to show)."""
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        # No `evidence=` passed — renderer can't resolve any id.
        **_kwargs(),
    )
    assert '<details class="evidence-drilldown">' not in html


def test_drilldown_handles_single_line_source_ref() -> None:
    """A source ref with line_start==line_end renders as just the line
    number (e.g. "12") not "12-12"."""
    ev = _ev(line_start=12, line_end=12)
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        evidence=[ev],
        **_kwargs(),
    )
    assert "main.tf:12<" in html


def test_drilldown_handles_no_line_range() -> None:
    """A source ref with no line_start/line_end (structural evidence —
    "this module has no CloudTrail at all") renders just the file."""
    ev = _ev(line_start=None, line_end=None)
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        evidence=[ev],
        **_kwargs(),
    )
    # Just the file, no colon-range suffix.
    assert ">main.tf<" in html
    assert "main.tf:" not in html


def test_drilldown_truncates_evidence_id_for_display() -> None:
    """Full sha256:... ids are 71 chars; the drill-down list truncates to
    the first 14 chars (sha256:aaaaaa) + ellipsis to keep the list
    scannable. The full id is still in the citations line above."""
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        evidence=[_ev()],
        **_kwargs(),
    )
    # The ellipsis appears inside the drill-down list. `eid[:14]` takes
    # the first 14 chars: "sha256:" (7 chars) + 7 hex.
    assert "sha256:aaaaaaa…" in html


# --- JSON sidecar `cited_evidence_refs` ------------------------------------


def test_json_sidecar_has_cited_evidence_refs_per_classification() -> None:
    """The JSON sidecar exposes `cited_evidence_refs` parallel to the
    HTML drill-down — same data, machine-readable. Tooling can use it
    to render its own drill-down without re-resolving evidence."""
    out = render_gap_report_json(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        evidence=[_ev()],
        **_kwargs(),
    )
    refs = out["ksi_classifications"][0]["cited_evidence_refs"]
    assert len(refs) == 1
    assert refs[0]["evidence_id"].startswith("sha256:")
    assert refs[0]["detector_id"] == "aws.tls_on_lb_listeners"
    assert refs[0]["source_file"] == "main.tf"
    assert refs[0]["source_lines"] == "12-24"


def test_json_sidecar_cited_refs_empty_when_no_evidence_passed() -> None:
    """No evidence list → empty refs (the evidence_ids field still
    populates from the classification, but no resolution is possible)."""
    out = render_gap_report_json(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        **_kwargs(),
    )
    refs = out["ksi_classifications"][0]["cited_evidence_refs"]
    assert refs == []


def test_json_sidecar_cited_refs_handles_unresolvable_ids() -> None:
    """A cited evidence_id that's not in the passed evidence list is
    silently skipped — the renderer can't add a source_file/lines
    without an Evidence record."""
    other_ev = _ev()
    clf = _classification(evidence_ids=["sha256:" + ("a" * 64), "sha256:" + ("z" * 64)])
    out = render_gap_report_json(
        _report(clf),
        evidence=[other_ev],  # only matches the first id
        **_kwargs(),
    )
    refs = out["ksi_classifications"][0]["cited_evidence_refs"]
    assert len(refs) == 1
    assert refs[0]["evidence_id"] == "sha256:" + ("a" * 64)


# --- _format_line_range helper --------------------------------------------


def test_format_line_range_helper() -> None:
    """The helper that produces "12-24" / "12" / None — directly tested
    so the JSON sidecar's source_lines values stay canonical."""
    from efterlev.reports.gap_report import _format_line_range

    assert _format_line_range(12, 24) == "12-24"
    assert _format_line_range(12, 12) == "12"
    assert _format_line_range(12, None) == "12"
    assert _format_line_range(None, 12) == "12"
    assert _format_line_range(None, None) is None
