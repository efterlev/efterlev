"""Deterministic, scanner-derived, high-trust records.

Evidence is what a `@detector` emits: a fact about the scanned source material,
with a verifiable `source_ref` pointing back to the file and line that produced
it. Evidence does not travel through an LLM — it is the raw signal the agents
reason over. The evidence-vs-claims discipline (see CLAUDE.md §Non-negotiable
principles) is enforced at this layer by keeping Evidence structurally distinct
from `Claim`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from efterlev.models._hashing import compute_content_id
from efterlev.models.source_ref import SourceRef

BoundaryState = Literal["in_boundary", "out_of_boundary", "boundary_undeclared"]
"""Authorization-boundary classification for an Evidence record. Priority 4
of v1-readiness-plan.md. The full taxonomy lives at `efterlev.boundary`;
this re-declaration is here because Evidence carries the field directly.
`boundary_undeclared` is the default — applies when no `[boundary]` config
is set in the workspace."""


class Evidence(BaseModel):
    """A single piece of scanner-derived evidence.

    `evidence_id` is the content-addressed id and is computed automatically on
    construction — callers should use `Evidence.create(...)` rather than passing
    an id explicitly. `model_validate(...)` is the deserialization path for
    records already in the provenance store and trusts the stored id.
    """

    model_config = ConfigDict(frozen=True)

    evidence_id: str = ""
    detector_id: str
    ksis_evidenced: list[str] = Field(default_factory=list)
    controls_evidenced: list[str] = Field(default_factory=list)
    source_ref: SourceRef
    content: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime
    # Priority 4 (2026-04-27): authorization-boundary scoping. Detectors emit
    # Evidence with this field set automatically by `Evidence.create` from the
    # active workspace boundary config (`efterlev.boundary.active_boundary_config`).
    # The default `boundary_undeclared` covers (a) workspaces with no
    # `[boundary]` config and (b) deserialization of older Evidence records
    # in existing stores. Adding the field changes `evidence_id` for newly-
    # created records (it's part of the content hash) — that's appropriate:
    # if the boundary changes, the same logical evidence is a different
    # record. Old records keep their old ids on load.
    boundary_state: BoundaryState = "boundary_undeclared"

    @model_validator(mode="after")
    def _compute_id(self) -> Evidence:
        if not self.evidence_id:
            object.__setattr__(
                self, "evidence_id", compute_content_id(self, exclude={"evidence_id"})
            )
        return self

    @classmethod
    def create(
        cls,
        *,
        detector_id: str,
        source_ref: SourceRef,
        ksis_evidenced: list[str] | None = None,
        controls_evidenced: list[str] | None = None,
        content: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
        boundary_state: BoundaryState | None = None,
    ) -> Evidence:
        """Construct an Evidence record with a freshly computed content id.

        When `boundary_state` is omitted, consults the active boundary
        context (`efterlev.boundary.get_active_boundary_config()`) and
        derives the state from `source_ref.file`. This is what lets
        detectors stay boundary-unaware: they call `Evidence.create(...)`
        with no `boundary_state`, and the right value flows in from the
        scan layer's context activation.

        Pass `boundary_state` explicitly only in tests or when the caller
        genuinely knows the state independent of the active config.
        """
        if boundary_state is None:
            # Lazy import to avoid an import cycle (efterlev.boundary
            # references Path / pathspec at module level).
            from efterlev.boundary import compute_boundary_state, get_active_boundary_config

            active = get_active_boundary_config()
            boundary_state = compute_boundary_state(source_ref.file, active)
        return cls(
            evidence_id="",
            detector_id=detector_id,
            ksis_evidenced=ksis_evidenced or [],
            controls_evidenced=controls_evidenced or [],
            source_ref=source_ref,
            content=content or {},
            timestamp=timestamp or datetime.now().astimezone(),
            boundary_state=boundary_state,
        )
