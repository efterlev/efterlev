"""LLM-reasoned output that must cite the Evidence it was reasoning over.

Claim is the counterpart to Evidence: everything an agent produces — narrative
draft, KSI classification, mapping proposal, remediation diff — comes back as a
Claim. The `requires_review` field is typed `Literal[True]` so the type system
rejects any attempt to construct a Claim that bypasses human review. The
`derived_from` list is validated at storage time (`validate_claim_provenance`)
to ensure every cited id resolves in the provenance store.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from efterlev.models._hashing import compute_content_id

ClaimType = Literal["narrative", "mapping", "remediation", "classification"]
Confidence = Literal["low", "medium", "high"]


class Claim(BaseModel):
    """A reasoned assertion that must carry DRAFT marking and evidence citations."""

    model_config = ConfigDict(frozen=True)

    claim_id: str = ""
    claim_type: ClaimType
    content: str | dict[str, Any]
    confidence: Confidence
    requires_review: Literal[True] = True
    derived_from: list[str] = Field(default_factory=list)
    model: str
    prompt_hash: str
    timestamp: datetime

    @model_validator(mode="after")
    def _compute_id(self) -> Claim:
        if not self.claim_id:
            object.__setattr__(self, "claim_id", compute_content_id(self, exclude={"claim_id"}))
        return self

    @classmethod
    def create(
        cls,
        *,
        claim_type: ClaimType,
        content: str | dict[str, Any],
        confidence: Confidence,
        derived_from: list[str],
        model: str,
        prompt_hash: str,
        timestamp: datetime | None = None,
    ) -> Claim:
        """Construct a Claim with a freshly computed content id."""
        return cls(
            claim_id="",
            claim_type=claim_type,
            content=content,
            confidence=confidence,
            derived_from=derived_from,
            model=model,
            prompt_hash=prompt_hash,
            timestamp=timestamp or datetime.now().astimezone(),
        )
