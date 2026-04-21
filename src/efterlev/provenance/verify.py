"""Receipt-log tamper detection.

Cross-checks every line in `.efterlev/receipts.log` against the SQLite store:
the intersection must match exactly. A record in the store without a receipt,
or a receipt without a matching record, is a tamper signal. Will be wrapped as
a `@primitive` in Phase 1c so agents can call it over MCP; ships as a plain
function at Phase 1b so tests can exercise it now.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from efterlev.provenance.store import ProvenanceStore


@dataclass
class VerifyReceiptsReport:
    """Typed result of a receipts/store cross-check."""

    clean: bool
    store_records: int
    receipts: int
    missing_receipts: list[str] = field(default_factory=list)
    """Records in the store that are NOT in receipts.log."""
    orphan_receipts: list[str] = field(default_factory=list)
    """Receipt lines whose record_id does NOT resolve in the store."""
    mismatched: list[str] = field(default_factory=list)
    """Record IDs present in both but with differing metadata fields."""


def verify_receipts(store: ProvenanceStore) -> VerifyReceiptsReport:
    """Walk the receipts log and SQLite store; report discrepancies."""
    store_ids = set(store.iter_records())
    receipt_entries = store.receipts.read_all()
    receipt_ids = {e["record_id"] for e in receipt_entries}

    missing_receipts = sorted(store_ids - receipt_ids)
    orphan_receipts = sorted(receipt_ids - store_ids)

    mismatched: list[str] = []
    for entry in receipt_entries:
        rid = entry["record_id"]
        if rid not in store_ids:
            continue
        stored = store.get_record(rid)
        if stored is None:
            continue
        if (
            entry["record_type"] != stored.record_type
            or entry["derived_from"] != list(stored.derived_from)
            or entry["primitive"] != stored.primitive
            or entry["agent"] != stored.agent
            or entry["model"] != stored.model
            or entry["prompt_hash"] != stored.prompt_hash
        ):
            mismatched.append(rid)

    return VerifyReceiptsReport(
        clean=not (missing_receipts or orphan_receipts or mismatched),
        store_records=len(store_ids),
        receipts=len(receipt_entries),
        missing_receipts=missing_receipts,
        orphan_receipts=orphan_receipts,
        mismatched=sorted(mismatched),
    )
