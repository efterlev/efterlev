"""Tests for the sort controls on the gap report.

Priority 2.8 (2026-04-28). The sort `<select>` lets reviewers reorder
classification cards by KSI (default), severity (most-actionable
first), or evidence count (descending). Cards live inside a
`.classifications-list` wrapper so JS can re-append them in order.

Tests cover the rendered DOM hooks; JS reordering itself is verified
visually in a browser.
"""

from __future__ import annotations

from datetime import UTC, datetime

from efterlev.agents import GapReport
from efterlev.agents.gap import KsiClassification
from efterlev.reports import render_gap_report_html


def _classification(
    ksi_id: str = "KSI-SVC-SNT",
    status: str = "partial",
    evidence_ids: list[str] | None = None,
) -> KsiClassification:
    return KsiClassification(
        ksi_id=ksi_id,
        status=status,  # type: ignore[arg-type]
        rationale="...",
        evidence_ids=evidence_ids
        if evidence_ids is not None
        else (["sha256:" + "a" * 64] if status in ("implemented", "partial") else []),
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


# --- sort select rendering -------------------------------------------------


def test_sort_select_renders_when_classifications_present() -> None:
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        **_kwargs(),
    )
    assert 'id="card-sort"' in html
    assert 'class="sort-select"' in html


def test_sort_options_match_design() -> None:
    """Three sort options: KSI (default), severity, evidence count."""
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        **_kwargs(),
    )
    assert 'value="ksi">By KSI<' in html
    assert 'value="severity">By severity<' in html
    assert 'value="evidence_count">By evidence count<' in html


def test_sort_omitted_when_no_classifications() -> None:
    html = render_gap_report_html(_report(), **_kwargs())
    assert 'id="card-sort"' not in html
    # The `.classifications-list` div wrapper is also omitted in the rendered
    # body (the JS still mentions the selector internally; that's fine —
    # `listEl` ends up null and the sort handler short-circuits).
    assert '<div class="classifications-list">' not in html


# --- list wrapper + data-evidence-count -----------------------------------


def test_classifications_list_wrapper_present() -> None:
    """Cards live inside `.classifications-list` so JS can sort by
    re-appending them in order."""
    html = render_gap_report_html(
        _report(
            _classification("KSI-SVC-SNT", status="partial"),
            _classification("KSI-IAM-MFA", status="not_implemented"),
        ),
        **_kwargs(),
    )
    assert '<div class="classifications-list">' in html
    # The wrapper opens before both cards (DOM well-formedness is implicit
    # via Jinja closing it after the loop).
    list_open_idx = html.index('<div class="classifications-list">')
    assert list_open_idx < html.index('id="ksi-KSI-SVC-SNT"')
    assert list_open_idx < html.index('id="ksi-KSI-IAM-MFA"')


def test_cards_carry_data_evidence_count() -> None:
    """Each card exposes evidence count via `data-evidence-count` so JS
    sort by evidence count is cheap (no traversal needed)."""
    html = render_gap_report_html(
        _report(
            _classification(
                "KSI-SVC-SNT",
                status="implemented",
                evidence_ids=["sha256:" + "a" * 64, "sha256:" + "b" * 64],
            ),
            _classification("KSI-IAM-MFA", status="not_implemented", evidence_ids=[]),
        ),
        **_kwargs(),
    )
    assert 'data-evidence-count="2"' in html
    assert 'data-evidence-count="0"' in html


# --- JS handler ------------------------------------------------------------


def test_sort_handler_registered() -> None:
    """JS attaches a `change` event listener on `#card-sort` and runs
    `applySort` to reorder cards inside `.classifications-list`."""
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        **_kwargs(),
    )
    assert "addEventListener('change', applySort)" in html
    assert ".classifications-list" in html
    assert "SEVERITY_RANK" in html


def test_severity_ranking_orders_actionable_findings_first() -> None:
    """The severity rank embedded in JS puts not_implemented first
    (most-actionable). Readers scanning a sorted report see real gaps
    at the top."""
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        **_kwargs(),
    )
    # Verify the embedded rank assigns 0 to not_implemented (top).
    assert "not_implemented: 0" in html
    assert "partial: 1" in html
    assert "implemented: 2" in html


# --- progressive enhancement ----------------------------------------------


def test_default_render_order_is_input_order() -> None:
    """With JS disabled, cards stay in the order Jinja emitted them
    (which is the input list's order). Sort is purely client-side."""
    html = render_gap_report_html(
        _report(
            _classification("KSI-SVC-SNT", status="implemented"),
            _classification("KSI-IAM-MFA", status="not_implemented"),
            _classification("KSI-CMT-LMC", status="partial"),
        ),
        **_kwargs(),
    )
    # Order in the rendered HTML = order in the input list.
    snt_idx = html.index('id="ksi-KSI-SVC-SNT"')
    mfa_idx = html.index('id="ksi-KSI-IAM-MFA"')
    lmc_idx = html.index('id="ksi-KSI-CMT-LMC"')
    assert snt_idx < mfa_idx < lmc_idx
