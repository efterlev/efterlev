"""S3 bucket public-access-block detector.

`aws_s3_bucket_public_access_block` is the AWS-recommended mechanism for
closing S3 to public reads/writes at the bucket level. Four independent
booleans govern the posture:

  - `block_public_acls`       — new ACLs with public grants are rejected.
  - `ignore_public_acls`      — existing public ACLs are treated as empty.
  - `block_public_policy`     — new bucket policies with public grants are
                                rejected.
  - `restrict_public_buckets` — buckets with cross-account / public policies
                                are restricted to the account owner.

All four must be `true` for "fully blocked." A resource missing any of the
four is partial coverage and is emitted as such.

Per the SC-28 precedent (DECISIONS 2026-04-21 design call #1, Option C):
FRMR 0.9.43-beta lists AC-3 in no KSI's `controls` array, so this detector
declares `ksis=[]` and surfaces at the 800-53 level only. The Gap Agent
renders such findings as "unmapped to any current KSI" — the honest
representation of the FRMR mapping gap.

Scope: this detector only examines declared `aws_s3_bucket_public_access_block`
resources. It does NOT cross-reference which buckets are covered vs. not —
the Gap Agent does that (mirroring the Phase 3 pattern used by
encryption_s3_at_rest's separate-resource case).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.models import Evidence, TerraformResource

_FLAGS = (
    "block_public_acls",
    "ignore_public_acls",
    "block_public_policy",
    "restrict_public_buckets",
)


@detector(
    id="aws.s3_public_access_block",
    ksis=[],  # AC-3 is not in any KSI's controls in FRMR 0.9.43-beta
    controls=["AC-3"],
    source="terraform",
    version="0.1.0",
)
def detect(resources: list[TerraformResource]) -> list[Evidence]:
    """Emit public-access-block posture Evidence for every PAB resource found.

    Evidences (800-53):  AC-3 (Access Enforcement) — declared enforcement
                         of bucket-level public-access restrictions.
    Evidences (KSI):     None — AC-3 is not currently mapped to any FRMR
                         KSI in 0.9.43-beta; see detector README.
    Does NOT prove:      that every bucket in the repo has a PAB resource;
                         that the account-level PAB is enabled (an
                         orthogonal AWS feature); that the applied bucket
                         policies themselves don't grant public access;
                         runtime state on deployed buckets.
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)

    for r in resources:
        if r.type != "aws_s3_bucket_public_access_block":
            continue
        flags = {flag: _coerce_bool(r.body.get(flag)) for flag in _FLAGS}
        all_true = all(v is True for v in flags.values())
        content: dict[str, Any] = {
            "resource_type": r.type,
            "resource_name": r.name,
            "posture": "fully_blocked" if all_true else "partial",
            "flags": flags,
        }
        if not all_true:
            missing = sorted(k for k, v in flags.items() if v is not True)
            content["gap"] = f"flags not set to true: {', '.join(missing)}"
        out.append(
            Evidence.create(
                detector_id="aws.s3_public_access_block",
                ksis_evidenced=[],
                controls_evidenced=["AC-3"],
                source_ref=r.source_ref,
                content=content,
                timestamp=now,
            )
        )

    return out


def _coerce_bool(value: Any) -> bool | None:
    """Return a bool for genuine booleans, None for absent / unparseable.

    HCL's declarative booleans come through as native Python `bool`. HCL
    string expressions (e.g. `"true"` or variables / locals) produce strings
    and cannot be statically evaluated here — we refuse to guess. Absent
    keys are treated as None, which correctly fails the "all true" check.
    """
    if isinstance(value, bool):
        return value
    return None
