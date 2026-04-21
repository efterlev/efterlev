"""Reference into source material that Evidence was extracted from.

`file` is always required; `line_start` / `line_end` are optional because some
evidence is structural (e.g., "this module has no CloudTrail resource at all")
and doesn't point at a specific line. `commit` is populated by the scan primitive
when the target repo is a git working tree.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class SourceRef(BaseModel):
    """Where in the scanned source material a piece of Evidence originated."""

    model_config = ConfigDict(frozen=True)

    file: Path
    line_start: int | None = None
    line_end: int | None = None
    commit: str | None = None
