"""SHA-256 content-addressing helper shared by every Efterlev record type.

The same canonicalization rule is used by `Evidence`, `Claim`, and
`ProvenanceRecord` so their IDs are reproducible from their content: dump
the model to JSON with sorted keys, exclude the id field itself, hash the
result. Prefixed with `sha256:` so future hash algorithm migrations are
self-describing (v1+ might add `blake3:` or `sha3:` if we need them).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel

HASH_PREFIX = "sha256:"


def _default(value: Any) -> Any:
    """JSON fallback for types json.dumps doesn't handle natively."""
    from datetime import datetime
    from pathlib import Path

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"unsupported type for canonical hashing: {type(value).__name__}")


def compute_content_id(model: BaseModel, *, exclude: set[str]) -> str:
    """Return the canonical `sha256:...` id for a model, excluding the id field itself."""
    payload = model.model_dump(mode="json", exclude=exclude)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_default)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{HASH_PREFIX}{digest}"
