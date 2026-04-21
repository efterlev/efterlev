"""NIST SP 800-53 Rev 5 control and enhancement types.

These mirror the small slice of the OSCAL catalog we actually use (id, title,
family, enhancements). We do not model every OSCAL property here; the full
OSCAL object can be loaded via `compliance-trestle` when the loader primitive
needs it. Control ids follow OSCAL's lowercase convention (`sc-28`, `sc-28.1`)
so they match the ids emitted by FRMR's `controls` arrays directly.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ControlEnhancement(BaseModel):
    """A 800-53 control enhancement (e.g., SC-28(1))."""

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "sc-28.1"
    parent_id: str  # e.g. "sc-28"
    title: str


class Control(BaseModel):
    """A 800-53 control and its enhancements."""

    model_config = ConfigDict(frozen=True)

    id: str  # e.g. "sc-28"
    family: str  # e.g. "sc"
    title: str
    enhancements: list[ControlEnhancement] = Field(default_factory=list)
