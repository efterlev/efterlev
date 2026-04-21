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
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from efterlev.models._hashing import compute_content_id
from efterlev.models.source_ref import SourceRef


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
    ) -> Evidence:
        """Construct an Evidence record with a freshly computed content id."""
        return cls(
            evidence_id="",
            detector_id=detector_id,
            ksis_evidenced=ksis_evidenced or [],
            controls_evidenced=controls_evidenced or [],
            source_ref=source_ref,
            content=content or {},
            timestamp=timestamp or datetime.now().astimezone(),
        )
