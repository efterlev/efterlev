"""Typed representation of source material detectors consume.

At v0 the only source type is Terraform/OpenTofu. `TerraformResource` wraps one
`resource "TYPE" "NAME" { ... }` block with its parsed attributes and the
`SourceRef` pointing back to the .tf file and line range. This is what
detectors iterate over; CLAUDE.md's detector contract references `TerraformResource`
in the example.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from efterlev.models.source_ref import SourceRef


class TerraformResource(BaseModel):
    """A single `resource "TYPE" "NAME" { ... }` block from a Terraform file."""

    model_config = ConfigDict(frozen=True)

    type: str
    name: str
    body: dict[str, Any] = Field(default_factory=dict)
    source_ref: SourceRef

    def get_nested(self, *keys: str) -> Any:
        """Walk the body dict by key path, returning None on any missing step.

        Terraform nested blocks are represented by python-hcl2 as lists of dicts
        (one entry per block instance). We unwrap single-element lists so
        detectors can chain `.get_nested("foo", "bar")` without manual index
        gymnastics for the common single-block case.
        """
        cur: Any = self.body
        for key in keys:
            if isinstance(cur, list) and len(cur) == 1:
                cur = cur[0]
            if not isinstance(cur, dict):
                return None
            cur = cur.get(key)
            if cur is None:
                return None
        if isinstance(cur, list) and len(cur) == 1:
            cur = cur[0]
        return cur
