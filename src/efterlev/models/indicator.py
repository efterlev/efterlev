"""FedRAMP 20x Key Security Indicator (KSI) — the user-facing compliance unit.

An `Indicator` is one KSI entry from the vendored FRMR (e.g., `KSI-SVC-SNT`
"Securing Network Traffic"). A `Theme` groups indicators by FRMR category (e.g.,
`SVC` "Service Configuration"). A `Baseline` selects which indicators apply to a
given authorization target (e.g., FedRAMP 20x Moderate); at v0 the baseline is
implicitly "all indicators in the vendored FRMR," but the type exists so future
baselines can carry their own subset.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Indicator(BaseModel):
    """One KSI indicator: the outcome FedRAMP 20x evaluates against."""

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "KSI-SVC-SNT"
    theme: str  # parent theme id, e.g. "SVC"
    name: str  # e.g. "Securing Network Traffic"
    statement: str | None  # the outcome text; may be absent for a few FRMR entries
    controls: list[str] = Field(default_factory=list)  # 800-53 ids, lowercased
    fka: str | None = None  # "formerly known as" id, for lineage across FRMR renames


class Theme(BaseModel):
    """A KSI theme: a named grouping of related indicators."""

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "SVC"
    name: str  # e.g. "Service Configuration"
    short_name: str | None = None
    description: str | None = None  # theme-level framing text from FRMR


class Baseline(BaseModel):
    """A named selection of KSI indicators constituting an authorization target."""

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "fedramp-20x-moderate"
    name: str  # e.g. "FedRAMP 20x Moderate"
    indicator_ids: list[str] = Field(default_factory=list)
