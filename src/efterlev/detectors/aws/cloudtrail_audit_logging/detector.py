"""AWS CloudTrail audit-logging detector.

Evidences KSI-MLA-LET ("Logging Event Types") and KSI-MLA-OSM
("Operating SIEM Capability") + 800-53 AU-2 ("Event Logging") and AU-12
("Audit Record Generation") at the infrastructure layer: we confirm
that an `aws_cloudtrail` resource exists and is configured to capture
management events across regions.

Evidence emitted per `aws_cloudtrail`:
  - `cloudtrail_state` — "present" if the trail is multi-region AND
    includes global service events; "partial" if either flag is missing
    or false; "absent" is not a valid per-resource state (a *resource*
    that exists is at minimum partial).
  - `is_multi_region` bool
  - `includes_global_events` bool
  - `has_event_selectors` bool — whether any event_selector block is
    present (management-event coverage signal)

Absence of any `aws_cloudtrail` resource produces **no** evidence — the
Gap Agent renders the KSI as `not_implemented` when it sees zero
evidence for a baseline KSI the detector covers.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.models import Evidence, TerraformResource


@detector(
    id="aws.cloudtrail_audit_logging",
    ksis=["KSI-MLA-LET", "KSI-MLA-OSM"],
    controls=["AU-2", "AU-12"],
    source="terraform",
    version="0.1.0",
)
def detect(resources: list[TerraformResource]) -> list[Evidence]:
    """Emit audit-logging Evidence for every `aws_cloudtrail` resource.

    Evidences (KSI):     KSI-MLA-LET (Logging Event Types),
                         KSI-MLA-OSM (Operating SIEM Capability) — partial.
    Evidences (800-53):  AU-2 (Event Logging), AU-12 (Audit Record Generation).
    Does NOT prove:      (1) downstream SIEM ingestion or alerting;
                         (2) log-retention policies against S3 lifecycle;
                         (3) log integrity (CloudTrail Lake, log-file
                         validation) — v1 additions;
                         (4) that the trail's S3 destination bucket has
                         appropriate access controls (separate detector).
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)
    for r in resources:
        if r.type != "aws_cloudtrail":
            continue
        out.append(_emit_trail_evidence(r, now))
    return out


def _emit_trail_evidence(r: TerraformResource, now: datetime) -> Evidence:
    is_multi_region = _as_bool(r.body.get("is_multi_region_trail"))
    includes_global = _as_bool(r.body.get("include_global_service_events"))
    # include_global_service_events defaults to true in the AWS provider;
    # treat missing attribute as True rather than False.
    if r.body.get("include_global_service_events") is None:
        includes_global = True

    has_event_selectors = bool(r.body.get("event_selector"))

    fully_covers = bool(is_multi_region) and bool(includes_global)
    state = "present" if fully_covers else "partial"

    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
        "cloudtrail_state": state,
        "is_multi_region": bool(is_multi_region),
        "includes_global_events": bool(includes_global),
        "has_event_selectors": has_event_selectors,
    }
    if state == "partial":
        missing: list[str] = []
        if not is_multi_region:
            missing.append("is_multi_region_trail")
        if not includes_global:
            missing.append("include_global_service_events")
        content["gap"] = (
            "trail declared but missing or disabled: " + ", ".join(missing)
            if missing
            else "trail declared with partial coverage"
        )

    return Evidence.create(
        detector_id="aws.cloudtrail_audit_logging",
        ksis_evidenced=["KSI-MLA-LET", "KSI-MLA-OSM"],
        controls_evidenced=["AU-2", "AU-12"],
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )


def _as_bool(value: Any) -> bool:
    """python-hcl2 may return True/False, "true"/"false", or single-element lists."""
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False
