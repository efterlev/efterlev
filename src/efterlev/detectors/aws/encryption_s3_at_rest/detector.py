"""S3 bucket at-rest encryption detector.

Per DECISIONS 2026-04-21 (design call #1, Option C): FRMR 0.9.43-beta lists
no KSI whose `controls` array contains SC-28, so this detector declares
`ksis=[]` and surfaces at the 800-53 level only. The Gap Agent renders such
findings as "unmapped to any current KSI" — the honest representation of
the FRMR mapping gap. We do not fudge VRI (which is SC-13 integrity) into
this detector's KSI set.

Evidence emitted per S3-related resource:

  - For each `aws_s3_bucket`:
      encryption_state = "present" | "absent"
      location         = "inline" when the bucket block contains
                          server_side_encryption_configuration; otherwise
                          absent (a separate resource may still cover it).
  - For each `aws_s3_bucket_server_side_encryption_configuration`:
      encryption_state = "present"
      location         = "separate_resource"

Cross-referencing between a bucket and its separate SSE resource is left to
the Gap Agent (Phase 3). v0 emits facts; reasoning is downstream.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.models import Evidence, TerraformResource


@detector(
    id="aws.encryption_s3_at_rest",
    ksis=[],  # DECISIONS 2026-04-21: SC-28 has no FRMR KSI in 0.9.43-beta
    controls=["SC-28", "SC-28(1)"],
    source="terraform",
    version="0.1.0",
)
def detect(resources: list[TerraformResource]) -> list[Evidence]:
    """Emit encryption-state Evidence for every S3 bucket and SSE resource found.

    Evidences (800-53):  SC-28 (Protection of Information at Rest).
                         SC-28(1) (Cryptographic Protection) when an
                         `sse_algorithm` is detectable in the configuration.
    Evidences (KSI):     None — SC-28 is not currently mapped to any FRMR
                         KSI in 0.9.43-beta; see the detector README for
                         the mapping-gap rationale.
    Does NOT prove:      key management practices, rotation, BYOK
                         (SC-12 territory; procedural evidence we cannot
                         see from Terraform source alone); whether a
                         bucket policy also enforces encryption for
                         client-side writes; runtime enforcement on
                         already-deployed objects.
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)

    for r in resources:
        if r.type == "aws_s3_bucket":
            out.append(_emit_bucket_evidence(r, now))
        elif r.type == "aws_s3_bucket_server_side_encryption_configuration":
            out.append(_emit_separate_sse_evidence(r, now))

    return out


def _emit_bucket_evidence(r: TerraformResource, now: datetime) -> Evidence:
    sse_block = r.get_nested("server_side_encryption_configuration")
    if sse_block:
        algorithm = _extract_algorithm(sse_block)
        content: dict[str, Any] = {
            "resource_type": r.type,
            "resource_name": r.name,
            "encryption_state": "present",
            "location": "inline",
        }
        if algorithm is not None:
            content["algorithm"] = algorithm
        # Enhancement (SC-28(1)) only when we can name the crypto method.
        controls = ["SC-28", "SC-28(1)"] if algorithm else ["SC-28"]
        return Evidence.create(
            detector_id="aws.encryption_s3_at_rest",
            ksis_evidenced=[],
            controls_evidenced=controls,
            source_ref=r.source_ref,
            content=content,
            timestamp=now,
        )

    return Evidence.create(
        detector_id="aws.encryption_s3_at_rest",
        ksis_evidenced=[],
        controls_evidenced=["SC-28"],
        source_ref=r.source_ref,
        content={
            "resource_type": r.type,
            "resource_name": r.name,
            "encryption_state": "absent",
            "gap": "bucket declared without inline server_side_encryption_configuration",
        },
        timestamp=now,
    )


def _emit_separate_sse_evidence(r: TerraformResource, now: datetime) -> Evidence:
    algorithm = _extract_algorithm(r.body)
    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
        "encryption_state": "present",
        "location": "separate_resource",
    }
    if algorithm is not None:
        content["algorithm"] = algorithm
    controls = ["SC-28", "SC-28(1)"] if algorithm else ["SC-28"]
    return Evidence.create(
        detector_id="aws.encryption_s3_at_rest",
        ksis_evidenced=[],
        controls_evidenced=controls,
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )


def _extract_algorithm(block: Any) -> str | None:
    """Dig into an SSE configuration block to find sse_algorithm, if any."""
    if isinstance(block, list) and len(block) == 1:
        block = block[0]
    if not isinstance(block, dict):
        return None
    rule = block.get("rule")
    if isinstance(rule, list) and len(rule) == 1:
        rule = rule[0]
    if not isinstance(rule, dict):
        return None
    default = rule.get("apply_server_side_encryption_by_default")
    if isinstance(default, list) and len(default) == 1:
        default = default[0]
    if not isinstance(default, dict):
        return None
    algo = default.get("sse_algorithm")
    return algo if isinstance(algo, str) else None
