"""CloudTrail log-file-validation detector.

Deepens the existing `cloudtrail_audit_logging` detector. That detector
covers AU-2 / AU-12 (event selection and audit-record generation) — this
one covers AU-9 (protection of audit information): the log-file integrity
digest AWS writes when `enable_log_file_validation = true` on an
`aws_cloudtrail` resource.

The two detectors run independently on the same `aws_cloudtrail`
resources. Each emits its own Evidence record; the Gap Agent cross-
references them at reasoning time.

FRMR 0.9.43-beta lists au-9 in KSI-MLA-OSM's `controls` array (the
Operating SIEM KSI — tamper-resistant logging is called out explicitly
in its statement). That mapping is clean — we claim it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.models import Evidence, TerraformResource


@detector(
    id="aws.cloudtrail_log_file_validation",
    ksis=["KSI-MLA-OSM"],
    controls=["AU-9"],
    source="terraform",
    version="0.1.0",
)
def detect(resources: list[TerraformResource]) -> list[Evidence]:
    """Emit log-file-validation Evidence for every aws_cloudtrail found.

    Evidences (800-53):  AU-9 (Protection of Audit Information) — trail
                         declares AWS-native log-file integrity digests.
    Evidences (KSI):     KSI-MLA-OSM (Operating SIEM) — tamper-resistant
                         logging is explicit in the KSI's statement, and
                         AU-9 is in its controls array (FRMR 0.9.43-beta).
    Does NOT prove:      that downstream log processing preserves the
                         integrity guarantee (e.g. re-indexed into a SIEM
                         without the digest), that AWS's validation is
                         periodically exercised, that the S3 bucket
                         holding logs has object-lock enabled to prevent
                         deletion, or runtime state.
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)

    for r in resources:
        if r.type != "aws_cloudtrail":
            continue
        out.append(_emit_trail_evidence(r, now))
    return out


def _emit_trail_evidence(r: TerraformResource, now: datetime) -> Evidence:
    validation = r.body.get("enable_log_file_validation")
    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
    }

    if validation is True:
        content["validation_status"] = "enabled"
    else:
        content["validation_status"] = "disabled"
        content["gap"] = "enable_log_file_validation not set to true"

    return Evidence.create(
        detector_id="aws.cloudtrail_log_file_validation",
        ksis_evidenced=["KSI-MLA-OSM"],
        controls_evidenced=["AU-9"],
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )
