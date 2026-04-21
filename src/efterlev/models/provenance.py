"""Append-only, content-addressed record of every Evidence / Claim / derived output.

A ProvenanceRecord is the node type in the provenance graph. Every record is
append-only: once stored, it is immutable; new content produces a new record.
The record's id is the content address; walking derives_from edges reconstructs
the chain from any generated sentence back to the source line that produced it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from efterlev.models._hashing import compute_content_id

RecordType = Literal["evidence", "claim", "finding", "mapping", "remediation"]


class ProvenanceRecord(BaseModel):
    """One node in the provenance graph; immutable once stored."""

    model_config = ConfigDict(frozen=True)

    record_id: str = ""
    record_type: RecordType
    content_ref: str
    derived_from: list[str] = Field(default_factory=list)
    primitive: str | None = None
    agent: str | None = None
    model: str | None = None
    prompt_hash: str | None = None
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _compute_id(self) -> ProvenanceRecord:
        if not self.record_id:
            object.__setattr__(self, "record_id", compute_content_id(self, exclude={"record_id"}))
        return self

    @classmethod
    def create(
        cls,
        *,
        record_type: RecordType,
        content_ref: str,
        derived_from: list[str] | None = None,
        primitive: str | None = None,
        agent: str | None = None,
        model: str | None = None,
        prompt_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> ProvenanceRecord:
        """Construct a ProvenanceRecord with a freshly computed content id."""
        return cls(
            record_id="",
            record_type=record_type,
            content_ref=content_ref,
            derived_from=derived_from or [],
            primitive=primitive,
            agent=agent,
            model=model,
            prompt_hash=prompt_hash,
            timestamp=timestamp or datetime.now().astimezone(),
            metadata=metadata or {},
        )
