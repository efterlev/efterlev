"""Tests for the coverage-matrix component on the gap report.

Priority 2.4 (2026-04-27). The matrix is the highest-visibility piece
of the HTML overhaul: a single-page heatmap showing every KSI in the
FRMR baseline color-coded by classification status, including KSIs the
agent didn't classify (rendered as `unclassified`).

Tests cover:
  - The pure data-shape function `build_coverage_matrix` — themes
    sorted, KSIs sorted within theme, status mapping, unclassified
    fallback, anchor IDs.
  - HTML output — matrix block present, cell anchors link to per-KSI
    classification cards which carry the matching `id="ksi-..."`.
  - JSON sidecar — same data emitted under `coverage_matrix`.
  - Backward compat — when themes/indicators aren't passed, matrix is
    omitted from HTML and is null in JSON.
"""

from __future__ import annotations

from datetime import UTC, datetime

from efterlev.agents import GapReport
from efterlev.agents.gap import KsiClassification
from efterlev.models import Indicator, Theme
from efterlev.reports import render_gap_report_html, render_gap_report_json
from efterlev.reports.gap_report import build_coverage_matrix


def _themes() -> dict[str, Theme]:
    return {
        "SVC": Theme(id="SVC", name="Service Configuration"),
        "IAM": Theme(id="IAM", name="Identity and Access Management"),
    }


def _indicators() -> dict[str, Indicator]:
    return {
        "KSI-SVC-SNT": Indicator(
            id="KSI-SVC-SNT", theme="SVC", name="Securing Network Traffic", statement="..."
        ),
        "KSI-SVC-VRI": Indicator(
            id="KSI-SVC-VRI", theme="SVC", name="Validating Resource Integrity", statement="..."
        ),
        "KSI-IAM-MFA": Indicator(
            id="KSI-IAM-MFA",
            theme="IAM",
            name="Enforcing Phishing-Resistant MFA",
            statement="...",
        ),
    }


def _classification(
    ksi_id: str = "KSI-SVC-SNT",
    status: str = "partial",
) -> KsiClassification:
    return KsiClassification(
        ksi_id=ksi_id,
        status=status,  # type: ignore[arg-type]
        rationale="...",
        evidence_ids=["sha256:" + "a" * 64] if status in ("implemented", "partial") else [],
    )


def _report(*classifications: KsiClassification) -> GapReport:
    return GapReport(
        ksi_classifications=list(classifications),
        unmapped_findings=[],
        claim_record_ids=[],
    )


def _baseline_kwargs() -> dict:
    return {
        "baseline_id": "fedramp-20x-moderate",
        "frmr_version": "0.9.43-beta",
        "generated_at": datetime(2026, 4, 27, 12, 0, 0, tzinfo=UTC),
    }


# --- build_coverage_matrix shape ------------------------------------------


def test_build_returns_none_when_themes_or_indicators_missing() -> None:
    """No FRMR → no matrix. The renderer omits the matrix section."""
    assert build_coverage_matrix(_report(), themes=None, indicators=None) is None
    assert build_coverage_matrix(_report(), themes=_themes(), indicators=None) is None
    assert build_coverage_matrix(_report(), themes=None, indicators=_indicators()) is None


def test_build_groups_ksis_by_theme_and_sorts() -> None:
    matrix = build_coverage_matrix(
        _report(),
        themes=_themes(),
        indicators=_indicators(),
    )
    assert matrix is not None
    # Themes ordered alphabetically: IAM, SVC.
    assert [t["id"] for t in matrix] == ["IAM", "SVC"]
    iam_theme = matrix[0]
    assert iam_theme["name"] == "Identity and Access Management"
    assert [c["id"] for c in iam_theme["ksis"]] == ["KSI-IAM-MFA"]
    svc_theme = matrix[1]
    # KSIs within theme sorted alphabetically: SNT before VRI.
    assert [c["id"] for c in svc_theme["ksis"]] == ["KSI-SVC-SNT", "KSI-SVC-VRI"]


def test_unclassified_ksis_get_unclassified_status() -> None:
    """KSI in FRMR but not in the report → status='unclassified'."""
    matrix = build_coverage_matrix(
        _report(_classification("KSI-SVC-SNT", status="implemented")),
        themes=_themes(),
        indicators=_indicators(),
    )
    assert matrix is not None
    cells_by_ksi = {c["id"]: c for theme in matrix for c in theme["ksis"]}
    assert cells_by_ksi["KSI-SVC-SNT"]["status"] == "implemented"
    assert cells_by_ksi["KSI-SVC-VRI"]["status"] == "unclassified"
    assert cells_by_ksi["KSI-IAM-MFA"]["status"] == "unclassified"


def test_classified_count_per_theme() -> None:
    matrix = build_coverage_matrix(
        _report(
            _classification("KSI-SVC-SNT", status="implemented"),
            _classification("KSI-SVC-VRI", status="not_implemented"),
        ),
        themes=_themes(),
        indicators=_indicators(),
    )
    assert matrix is not None
    by_id = {t["id"]: t for t in matrix}
    assert by_id["SVC"]["classified_count"] == 2
    assert by_id["IAM"]["classified_count"] == 0


def test_cell_suffix_extracted() -> None:
    """KSI suffix (last 3 chars after second hyphen) populated for cell label."""
    matrix = build_coverage_matrix(_report(), themes=_themes(), indicators=_indicators())
    assert matrix is not None
    suffixes = {c["id"]: c["suffix"] for theme in matrix for c in theme["ksis"]}
    assert suffixes["KSI-SVC-SNT"] == "SNT"
    assert suffixes["KSI-IAM-MFA"] == "MFA"


def test_cell_anchor_matches_classification_card_id() -> None:
    """Cell anchor is `ksi-<KSI-ID>` — must match the id attribute on the
    classification card so cell-click scrolls to the right card."""
    matrix = build_coverage_matrix(_report(), themes=_themes(), indicators=_indicators())
    assert matrix is not None
    anchors = {c["id"]: c["anchor"] for theme in matrix for c in theme["ksis"]}
    assert anchors["KSI-SVC-SNT"] == "ksi-KSI-SVC-SNT"


def test_theme_with_no_indicators_omitted() -> None:
    """A theme that has no indicators in the FRMR doesn't appear in the
    matrix — empty rows would just confuse the reader."""
    themes = _themes() | {"AFR": Theme(id="AFR", name="Authorization Framework")}
    # No KSI-AFR-* in indicators.
    matrix = build_coverage_matrix(_report(), themes=themes, indicators=_indicators())
    assert matrix is not None
    assert "AFR" not in [t["id"] for t in matrix]


# --- HTML rendering --------------------------------------------------------


def test_html_renders_coverage_matrix_section() -> None:
    """The matrix section appears between meta and Summary, with one cell
    per FRMR-listed KSI."""
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="implemented")),
        themes=_themes(),
        indicators=_indicators(),
        **_baseline_kwargs(),
    )
    assert ">Coverage matrix<" in html
    assert 'class="coverage-matrix"' in html
    # All three KSIs from the FRMR fixture show up as cells.
    assert "KSI-SVC-SNT" in html
    assert "KSI-SVC-VRI" in html
    assert "KSI-IAM-MFA" in html
    # Status classes applied.
    assert "matrix-cell status-implemented" in html
    assert "matrix-cell status-unclassified" in html


def test_html_classification_cards_carry_anchor_ids() -> None:
    """Cell anchors link to `#ksi-<KSI-ID>`; the classification card must
    carry `id="ksi-<KSI-ID>"` so the anchor resolves."""
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        themes=_themes(),
        indicators=_indicators(),
        **_baseline_kwargs(),
    )
    assert 'id="ksi-KSI-SVC-SNT"' in html
    # And the matrix cell links to that same anchor.
    assert 'href="#ksi-KSI-SVC-SNT"' in html


def test_html_omits_matrix_when_themes_indicators_not_passed() -> None:
    """Backward compat: existing callers that don't pass themes/indicators
    still get a valid report, just without the matrix section."""
    html = render_gap_report_html(
        _report(_classification("KSI-SVC-SNT", status="partial")),
        **_baseline_kwargs(),
    )
    assert ">Coverage matrix<" not in html
    assert 'class="coverage-matrix"' not in html


# --- JSON sidecar ----------------------------------------------------------


def test_json_sidecar_includes_coverage_matrix_when_passed() -> None:
    out = render_gap_report_json(
        _report(_classification("KSI-SVC-SNT", status="implemented")),
        themes=_themes(),
        indicators=_indicators(),
        **_baseline_kwargs(),
    )
    matrix = out["coverage_matrix"]
    assert matrix is not None
    assert isinstance(matrix, list)
    assert len(matrix) == 2  # IAM, SVC
    by_id = {t["id"]: t for t in matrix}
    svc_cells = {c["id"]: c["status"] for c in by_id["SVC"]["ksis"]}
    assert svc_cells["KSI-SVC-SNT"] == "implemented"
    assert svc_cells["KSI-SVC-VRI"] == "unclassified"


def test_json_sidecar_matrix_null_when_themes_indicators_not_passed() -> None:
    """Backward compat: omitting themes/indicators yields null matrix."""
    out = render_gap_report_json(_report(), **_baseline_kwargs())
    assert out["coverage_matrix"] is None
