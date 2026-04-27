"""Authorization-boundary scoping tests (Priority 4 of v1-readiness-plan)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from efterlev.boundary import (
    active_boundary_config,
    compute_boundary_state,
    get_active_boundary_config,
)
from efterlev.config import BoundaryConfig
from efterlev.models import Evidence, SourceRef

# --- compute_boundary_state ------------------------------------------------


def test_no_config_yields_undeclared() -> None:
    assert compute_boundary_state(Path("infra/main.tf"), None) == "boundary_undeclared"


def test_empty_config_yields_undeclared() -> None:
    cfg = BoundaryConfig()
    assert compute_boundary_state(Path("infra/main.tf"), cfg) == "boundary_undeclared"


def test_include_only_match_is_in_boundary() -> None:
    cfg = BoundaryConfig(include=["boundary/**"])
    assert compute_boundary_state(Path("boundary/main.tf"), cfg) == "in_boundary"
    assert compute_boundary_state(Path("boundary/sub/iam.tf"), cfg) == "in_boundary"


def test_include_only_non_match_is_out_of_boundary() -> None:
    """An include declaration creates an explicit scope; paths outside are out."""
    cfg = BoundaryConfig(include=["boundary/**"])
    assert compute_boundary_state(Path("infra/main.tf"), cfg) == "out_of_boundary"
    assert compute_boundary_state(Path("commercial/eks.tf"), cfg) == "out_of_boundary"


def test_exclude_only_match_is_out_of_boundary() -> None:
    """exclude-only means 'everything except these'."""
    cfg = BoundaryConfig(exclude=["commercial/**"])
    assert compute_boundary_state(Path("commercial/main.tf"), cfg) == "out_of_boundary"


def test_exclude_only_non_match_is_in_boundary() -> None:
    """exclude-only means everything not excluded is in scope."""
    cfg = BoundaryConfig(exclude=["commercial/**"])
    assert compute_boundary_state(Path("infra/main.tf"), cfg) == "in_boundary"
    assert compute_boundary_state(Path("boundary/sub/iam.tf"), cfg) == "in_boundary"


def test_exclude_wins_over_include() -> None:
    """A path matching both include and exclude is out_of_boundary.

    Rationale: explicit exclusion is a signal of intent; a broader inclusion
    should not silently override it. Customer-friendly precedence — `.gitignore`
    semantics that customers already understand."""
    cfg = BoundaryConfig(
        include=["infra/**"],
        exclude=["infra/legacy/**"],
    )
    assert compute_boundary_state(Path("infra/legacy/old.tf"), cfg) == "out_of_boundary"
    assert compute_boundary_state(Path("infra/prod/main.tf"), cfg) == "in_boundary"


def test_recursive_double_star() -> None:
    """`**` matches any number of intermediate directories."""
    cfg = BoundaryConfig(include=["**/main.tf"])
    assert compute_boundary_state(Path("main.tf"), cfg) == "in_boundary"
    assert compute_boundary_state(Path("a/main.tf"), cfg) == "in_boundary"
    assert compute_boundary_state(Path("a/b/c/main.tf"), cfg) == "in_boundary"
    assert compute_boundary_state(Path("a/b.tf"), cfg) == "out_of_boundary"


def test_directory_pattern_matches_recursively_per_gitignore_semantics() -> None:
    """gitwildmatch / .gitignore semantics: a pattern that matches a directory
    matches everything under it. So `boundary/*` matches `boundary/main.tf`
    AND `boundary/sub/main.tf` because `boundary/sub` matches and the file is
    under it. Customer-friendly: customers writing either `boundary/*` or
    `boundary/**` get the same "everything under boundary/" result.

    The narrower "files directly in boundary, no recursion" semantic is
    expressible via something like `boundary/*.tf` (one segment, file
    extension restricted) — which is what customers typically want when they
    care about non-recursion."""
    cfg = BoundaryConfig(include=["boundary/*"])
    assert compute_boundary_state(Path("boundary/main.tf"), cfg) == "in_boundary"
    assert compute_boundary_state(Path("boundary/sub/main.tf"), cfg) == "in_boundary"


def test_extension_pattern_at_root_is_non_recursive() -> None:
    """`*.tf` at the root level — files with .tf extension at root, but the
    pattern travels (per gitignore semantics) so `*.tf` actually matches at
    every level when not anchored. Customers wanting "only root .tf" use
    a leading `/` per gitignore: `/*.tf`."""
    cfg = BoundaryConfig(include=["*.tf"])
    assert compute_boundary_state(Path("main.tf"), cfg) == "in_boundary"
    # `*.tf` un-anchored matches at any depth — gitignore semantics.
    assert compute_boundary_state(Path("a/b/c.tf"), cfg) == "in_boundary"


# --- active_boundary_config context ----------------------------------------


def test_get_active_returns_none_outside_context() -> None:
    assert get_active_boundary_config() is None


def test_active_context_sets_and_restores() -> None:
    cfg = BoundaryConfig(include=["x/**"])
    assert get_active_boundary_config() is None
    with active_boundary_config(cfg):
        assert get_active_boundary_config() is cfg
    assert get_active_boundary_config() is None


def test_active_context_nested() -> None:
    """Nested activation respects scope: inner shadows outer; outer restored on exit."""
    outer = BoundaryConfig(include=["a/**"])
    inner = BoundaryConfig(include=["b/**"])
    with active_boundary_config(outer):
        assert get_active_boundary_config() is outer
        with active_boundary_config(inner):
            assert get_active_boundary_config() is inner
        assert get_active_boundary_config() is outer
    assert get_active_boundary_config() is None


# --- Evidence.create boundary integration ---------------------------------


def _ev(file: str = "infra/main.tf", **kwargs: object) -> Evidence:
    return Evidence.create(
        detector_id="aws.test",
        source_ref=SourceRef(file=Path(file), line_start=1, line_end=2),
        timestamp=datetime(2026, 4, 27, tzinfo=UTC),
        **kwargs,  # type: ignore[arg-type]
    )


def test_evidence_create_default_is_undeclared_without_active_config() -> None:
    ev = _ev()
    assert ev.boundary_state == "boundary_undeclared"


def test_evidence_create_picks_up_active_config() -> None:
    cfg = BoundaryConfig(include=["boundary/**"], exclude=["boundary/legacy/**"])
    with active_boundary_config(cfg):
        in_scope = _ev(file="boundary/main.tf")
        out_explicit = _ev(file="boundary/legacy/old.tf")
        out_implicit = _ev(file="commercial/eks.tf")
    assert in_scope.boundary_state == "in_boundary"
    assert out_explicit.boundary_state == "out_of_boundary"
    assert out_implicit.boundary_state == "out_of_boundary"


def test_evidence_create_explicit_boundary_state_overrides_context() -> None:
    """Explicit boundary_state arg trumps active context (test/utility path)."""
    cfg = BoundaryConfig(include=["boundary/**"])
    with active_boundary_config(cfg):
        ev = _ev(file="commercial/eks.tf", boundary_state="in_boundary")
    assert ev.boundary_state == "in_boundary"


def test_boundary_state_is_part_of_evidence_id() -> None:
    """Adding boundary_state to the model means logically-equivalent Evidence
    in different boundary contexts hashes differently — appropriate, since the
    boundary changes the meaning of the record."""
    e1 = _ev(boundary_state="in_boundary")
    e2 = _ev(boundary_state="out_of_boundary")
    e3 = _ev(boundary_state="boundary_undeclared")
    assert e1.evidence_id != e2.evidence_id
    assert e1.evidence_id != e3.evidence_id
    assert e2.evidence_id != e3.evidence_id


# --- BoundaryConfig schema -------------------------------------------------


def test_boundary_config_default_is_empty_lists() -> None:
    cfg = BoundaryConfig()
    assert cfg.include == []
    assert cfg.exclude == []


def test_boundary_config_round_trip_through_save_load(tmp_path: Path) -> None:
    """Save + load round-trips include/exclude through TOML cleanly."""
    from efterlev.config import Config, load_config, save_config

    cfg = Config(
        boundary=BoundaryConfig(include=["boundary/**", "infra/prod/**"], exclude=["**/test/**"])
    )
    path = tmp_path / "config.toml"
    save_config(cfg, path)
    restored = load_config(path)
    assert restored.boundary.include == ["boundary/**", "infra/prod/**"]
    assert restored.boundary.exclude == ["**/test/**"]


def test_save_config_omits_boundary_section_when_empty(tmp_path: Path) -> None:
    """Empty BoundaryConfig is the default (boundary_undeclared); the section
    should not appear in saved TOML — keeps the file minimal and avoids
    suggesting a meaningful empty declaration."""
    from efterlev.config import Config, save_config

    cfg = Config()
    path = tmp_path / "config.toml"
    save_config(cfg, path)
    text = path.read_text()
    assert "[boundary]" not in text


def test_load_config_accepts_missing_boundary_section(tmp_path: Path) -> None:
    """A hand-edited config without `[boundary]` should load cleanly with the
    default empty BoundaryConfig (boundary_undeclared)."""
    from efterlev.config import load_config

    toml = tmp_path / "no_boundary.toml"
    toml.write_text(
        "[llm]\n"
        'backend = "anthropic"\n'
        'fallback_model = "claude-sonnet-4-6"\n'
        "\n[scan]\n"
        'target_dir = "."\n'
        'output_dir = "./out"\n'
        "\n[baseline]\n"
        'id = "fedramp-20x-moderate"\n'
    )
    config = load_config(toml)
    assert config.boundary.include == []
    assert config.boundary.exclude == []


def test_boundary_config_rejects_unknown_field() -> None:
    """`extra="forbid"` on the model — a typo'd field surfaces immediately."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        BoundaryConfig(includes=["x"])  # type: ignore[call-arg]
