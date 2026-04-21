"""Recursive chain walker for the provenance graph.

Given a record_id, follows `derived_from` edges back to the leaves (records
with no parents) and returns a tree the CLI can pretty-print. Cycle detection
exists as a defence against corrupted stores — the graph should be a DAG by
construction, but we don't trust blindly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from efterlev.errors import ProvenanceError
from efterlev.models import ProvenanceRecord
from efterlev.provenance.store import ProvenanceStore


@dataclass
class ChainNode:
    """One node in a walked chain, plus its resolved parents."""

    record: ProvenanceRecord
    parents: list[ChainNode] = field(default_factory=list)


def walk_chain(store: ProvenanceStore, record_id: str) -> ChainNode:
    """Resolve the record and its full ancestor tree.

    Raises ProvenanceError if the requested record is missing or if the graph
    contains a cycle (the latter implies store corruption — the record_id
    comes from content hashing, so cycles are structurally impossible in a
    correctly-populated store).
    """
    visiting: set[str] = set()

    def _walk(rid: str) -> ChainNode:
        if rid in visiting:
            raise ProvenanceError(f"cycle in provenance graph at {rid}")
        record = store.get_record(rid)
        if record is None:
            raise ProvenanceError(f"record not found: {rid}")
        visiting.add(rid)
        try:
            parents = [_walk(parent_id) for parent_id in record.derived_from]
        finally:
            visiting.discard(rid)
        return ChainNode(record=record, parents=parents)

    return _walk(record_id)


def render_chain_text(root: ChainNode, indent: int = 0) -> str:
    """Render a chain as an indented ASCII tree for terminal output."""
    prefix = "  " * indent
    r = root.record
    origin = (
        f"primitive={r.primitive}"
        if r.primitive
        else f"agent={r.agent}"
        if r.agent
        else "origin=unknown"
    )
    if r.model:
        origin += f" model={r.model}"
    head = f"{prefix}{'└── ' if indent else ''}{r.record_id}  ({r.record_type})"
    meta = f"{prefix}    {origin}  at {r.timestamp.isoformat()}"
    body = f"{prefix}    content_ref={r.content_ref}"

    out = [head, meta, body]
    if not root.parents:
        out.append(f"{prefix}    (leaf — no derived_from)")
    else:
        for parent in root.parents:
            out.append(render_chain_text(parent, indent + 1))
    return "\n".join(out)
