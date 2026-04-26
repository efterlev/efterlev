"""Tests for store-level `validate_claim_provenance` defense-in-depth check.

A Claim's `derived_from` must cite ids that resolve in the store —
either directly as `ProvenanceRecord.record_id` or indirectly as
`Evidence.evidence_id` in a stored evidence record's payload. The
dual-lookup exists because agents' derived_from carries evidence_ids
(what the model saw in its prompt's fence), which are a different hash
from the record_id of the envelope that wrapped the Evidence when it
was stored.

Store-write-time validation is the secondary enforcement of claim-
citation integrity. The primary enforcement is per-agent fence
validators (`_validate_cited_ids` in gap.py / documentation.py /
remediation.py). This check catches agent bugs or direct store-write
paths that bypass the agent layer.

See DECISIONS 2026-04-23 "Store-level validate_claim_provenance".
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from efterlev.errors import ProvenanceError
from efterlev.models import Evidence, SourceRef
from efterlev.provenance import ProvenanceStore


def _ev(resource: str = "r0") -> Evidence:
    return Evidence.create(
        detector_id="aws.encryption_s3_at_rest",
        source_ref=SourceRef(file="main.tf", line_start=1, line_end=5),
        ksis_evidenced=[],
        controls_evidenced=["SC-28"],
        content={"resource_name": resource, "encryption_state": "present"},
        timestamp=datetime(2026, 4, 23, tzinfo=UTC),
    )


# --- happy paths -----------------------------------------------------------


def test_claim_citing_evidence_by_evidence_id_accepted(tmp_path: Path) -> None:
    """Gap Agent's usage pattern: evidence is stored; the claim's
    derived_from cites Evidence.evidence_id (the hash stored in the
    payload). Validation must accept this."""
    ev = _ev()
    with ProvenanceStore(tmp_path) as store:
        store.write_record(
            payload=ev.model_dump(mode="json"),
            record_type="evidence",
            primitive="aws.encryption_s3_at_rest@0.1.0",
        )
        # Now write a claim citing the evidence_id (not the record_id).
        claim = store.write_record(
            payload={"status": "partial", "rationale": "test"},
            record_type="claim",
            derived_from=[ev.evidence_id],
            agent="gap_agent@0.1.0",
        )
        assert claim.record_id  # Write succeeded.


def test_claim_citing_evidence_by_record_id_accepted(tmp_path: Path) -> None:
    """The alternate usage pattern: citing the ProvenanceRecord.record_id
    directly. Validation must accept this too."""
    with ProvenanceStore(tmp_path) as store:
        ev_record = store.write_record(
            payload={"x": 1},
            record_type="evidence",
        )
        claim = store.write_record(
            payload={"y": 2},
            record_type="claim",
            derived_from=[ev_record.record_id],
        )
        assert claim.record_id


def test_claim_with_empty_derived_from_accepted(tmp_path: Path) -> None:
    """A claim with no citations is allowed — not every claim derives
    from prior evidence (e.g. a whole-baseline summary)."""
    with ProvenanceStore(tmp_path) as store:
        claim = store.write_record(
            payload={"status": "implemented"},
            record_type="claim",
        )
        assert claim.record_id


def test_claim_citing_multiple_mixed_id_types_accepted(tmp_path: Path) -> None:
    """Real-world case: a claim cites some ids by evidence_id and
    others by record_id (mixed calling conventions across helpers).
    Validation must handle both in the same derived_from list."""
    first_ev = _ev(resource="a")
    with ProvenanceStore(tmp_path) as store:
        # Persist Evidence A via its evidence_id pathway.
        store.write_record(
            payload=first_ev.model_dump(mode="json"),
            record_type="evidence",
        )
        # Persist a raw evidence-typed record to get a record_id.
        raw_record = store.write_record(
            payload={"raw": "data"},
            record_type="evidence",
        )
        # Claim cites both.
        claim = store.write_record(
            payload={"status": "partial"},
            record_type="claim",
            derived_from=[first_ev.evidence_id, raw_record.record_id],
        )
        assert claim.record_id


# --- unhappy paths: fabricated / missing ids -----------------------------


def test_claim_with_unresolvable_id_rejected(tmp_path: Path) -> None:
    """A claim citing an id that isn't in the store MUST be rejected.
    This is the core defense-in-depth guarantee: a buggy agent or a
    direct store-write cannot persist a claim with a fabricated
    citation."""
    fake_id = "sha256:" + "0" * 64
    with ProvenanceStore(tmp_path) as store, pytest.raises(ProvenanceError, match="do not resolve"):
        store.write_record(
            payload={"status": "partial"},
            record_type="claim",
            derived_from=[fake_id],
        )


def test_rejection_happens_before_insert(tmp_path: Path) -> None:
    """Validation must run BEFORE the record is persisted — a rejected
    claim leaves the store unchanged. Checking the receipt log count
    confirms no partial write occurred."""
    fake_id = "sha256:" + "0" * 64
    with ProvenanceStore(tmp_path) as store:
        # Write a legitimate evidence record so the receipts log has
        # one entry pre-attempt.
        store.write_record(payload={"a": 1}, record_type="evidence")
        pre_count = len(list(store.iter_records()))

        with pytest.raises(ProvenanceError):
            store.write_record(
                payload={"status": "partial"},
                record_type="claim",
                derived_from=[fake_id],
            )

        post_count = len(list(store.iter_records()))
        # Store has NOT grown — the rejected claim never landed.
        assert post_count == pre_count


def test_partial_resolution_still_raises(tmp_path: Path) -> None:
    """A claim citing a mix of resolvable and fabricated ids must
    still raise — partial resolution isn't acceptable. The error
    message names the FIRST unresolved id for diagnostics."""
    ev = _ev()
    fake_id = "sha256:" + "d" * 64
    with ProvenanceStore(tmp_path) as store:
        store.write_record(
            payload=ev.model_dump(mode="json"),
            record_type="evidence",
        )
        with pytest.raises(ProvenanceError, match="do not resolve"):
            store.write_record(
                payload={"status": "partial"},
                record_type="claim",
                derived_from=[ev.evidence_id, fake_id],
            )


def test_multiple_missing_ids_reported_in_count(tmp_path: Path) -> None:
    fake_a = "sha256:" + "1" * 64
    fake_b = "sha256:" + "2" * 64
    fake_c = "sha256:" + "3" * 64
    with ProvenanceStore(tmp_path) as store, pytest.raises(ProvenanceError, match="3 evidence id"):
        store.write_record(
            payload={"status": "partial"},
            record_type="claim",
            derived_from=[fake_a, fake_b, fake_c],
        )


# --- validation scope: only claims -----------------------------------------


def test_evidence_records_skip_validation(tmp_path: Path) -> None:
    """Evidence records don't have a `derived_from`-validation concern —
    they ARE the primary source type. Writing an evidence record with
    unresolvable derived_from ids should succeed (if anything ever does
    that; the important property is that validation doesn't fire for
    non-claim types)."""
    fake_id = "sha256:" + "0" * 64
    with ProvenanceStore(tmp_path) as store:
        # This is unusual but should not be rejected by our validation,
        # which only fires for record_type="claim".
        record = store.write_record(
            payload={"x": 1},
            record_type="evidence",
            derived_from=[fake_id],
        )
        assert record.record_id


def test_finding_records_skip_validation(tmp_path: Path) -> None:
    """record_type values other than "claim" bypass the validation.
    Finding / mapping / remediation could be added later; only
    "claim" is defense-in-depth-checked at v0."""
    fake_id = "sha256:" + "0" * 64
    with ProvenanceStore(tmp_path) as store:
        record = store.write_record(
            payload={"x": 1},
            record_type="finding",
            derived_from=[fake_id],
        )
        assert record.record_id


# --- integration with real Evidence -------------------------------------


def test_real_evidence_objects_roundtrip(tmp_path: Path) -> None:
    """Real Evidence objects (as emitted by detectors) use sha256-
    prefixed ids. Verify the validator handles this shape correctly."""
    ev1 = _ev(resource="bucket-one")
    ev2 = _ev(resource="bucket-two")
    with ProvenanceStore(tmp_path) as store:
        store.write_record(
            payload=ev1.model_dump(mode="json"),
            record_type="evidence",
        )
        store.write_record(
            payload=ev2.model_dump(mode="json"),
            record_type="evidence",
        )

        # Both evidence_ids resolve.
        claim = store.write_record(
            payload={"summary": "mixed"},
            record_type="claim",
            derived_from=[ev1.evidence_id, ev2.evidence_id],
        )
        assert claim.record_id
