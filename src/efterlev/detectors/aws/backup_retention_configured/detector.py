"""AWS backup / retention detector.

Evidences KSI-RPL-ABO ("Aligning Backups with Objectives") and 800-53
CP-9 ("System Backup") at the infrastructure layer: we confirm that
backup mechanisms are configured on stateful resources — RDS instances
and clusters have a positive `backup_retention_period`, S3 buckets have
versioning enabled (via `aws_s3_bucket_versioning` or legacy inline
block).

Per CLAUDE.md's scope note: this detector proves that backup mechanics
exist, not that the retention duration is aligned with the user's
recovery-time / recovery-point objectives. The "alignment" half of
KSI-RPL-ABO is a procedural claim the scanner cannot evaluate.

Resource types inspected:
  - `aws_db_instance` — RDS single-AZ / standalone instance
  - `aws_rds_cluster` — Aurora / multi-AZ cluster
  - `aws_s3_bucket_versioning` — modern separate versioning resource
  - `aws_s3_bucket` — legacy inline `versioning` block (AWS provider <4.0)

Evidence emitted per resource:
  - `backup_state` — "present" | "absent"
  - `mechanism` — "rds_retention" | "s3_versioning"
  - `retention_days` (RDS only) — integer value of the retention period
  - `versioning_status` (S3 only) — "Enabled" | "Suspended" | "Disabled"
  - `gap` string when `backup_state="absent"`
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.models import Evidence, TerraformResource

_RDS_TYPES = {"aws_db_instance", "aws_rds_cluster"}


@detector(
    id="aws.backup_retention_configured",
    ksis=["KSI-RPL-ABO"],
    controls=["CP-9"],
    source="terraform",
    version="0.1.0",
)
def detect(resources: list[TerraformResource]) -> list[Evidence]:
    """Emit backup-state Evidence for every RDS / S3-versioning resource.

    Evidences (KSI):     KSI-RPL-ABO (Aligning Backups with Objectives) —
                         partial. Proves backup mechanics exist; does not
                         prove alignment with recovery objectives.
    Evidences (800-53):  CP-9 (System Backup).
    Does NOT prove:      RTO/RPO alignment (procedural); cross-region
                         replication (separate detector, v1); restore-
                         testing practices (procedural); whether backups
                         are themselves encrypted or access-controlled.
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)
    for r in resources:
        if r.type in _RDS_TYPES:
            out.append(_emit_rds_evidence(r, now))
        elif r.type == "aws_s3_bucket_versioning":
            out.append(_emit_s3_versioning_evidence(r, now))
        elif r.type == "aws_s3_bucket":
            # Only emit if the legacy inline `versioning { enabled = true }`
            # block is present — emitting "absent" for every bucket would
            # conflict with the versioning resource that may cover it from
            # a separate file.
            legacy = r.get_nested("versioning")
            if legacy is not None:
                out.append(_emit_legacy_s3_versioning_evidence(r, legacy, now))
    return out


def _emit_rds_evidence(r: TerraformResource, now: datetime) -> Evidence:
    retention_raw = r.body.get("backup_retention_period")
    if isinstance(retention_raw, list) and len(retention_raw) == 1:
        retention_raw = retention_raw[0]

    try:
        retention = int(retention_raw) if retention_raw is not None else None
    except (TypeError, ValueError):
        retention = None

    state = "present" if retention and retention > 0 else "absent"
    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
        "mechanism": "rds_retention",
        "backup_state": state,
    }
    if retention is not None:
        content["retention_days"] = retention
    if state == "absent":
        content["gap"] = (
            "backup_retention_period is 0 or unset; RDS automated backups will not be retained"
        )

    return Evidence.create(
        detector_id="aws.backup_retention_configured",
        ksis_evidenced=["KSI-RPL-ABO"],
        controls_evidenced=["CP-9"],
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )


def _emit_s3_versioning_evidence(r: TerraformResource, now: datetime) -> Evidence:
    config = r.get_nested("versioning_configuration")
    status = None
    if isinstance(config, dict):
        status_raw = config.get("status")
        if isinstance(status_raw, list) and len(status_raw) == 1:
            status_raw = status_raw[0]
        if isinstance(status_raw, str):
            status = status_raw

    state = "present" if status == "Enabled" else "absent"
    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
        "mechanism": "s3_versioning",
        "backup_state": state,
    }
    if status is not None:
        content["versioning_status"] = status
    if state == "absent":
        content["gap"] = (
            f"aws_s3_bucket_versioning status is {status!r}; object "
            "version history will not be retained for recovery"
        )

    return Evidence.create(
        detector_id="aws.backup_retention_configured",
        ksis_evidenced=["KSI-RPL-ABO"],
        controls_evidenced=["CP-9"],
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )


def _emit_legacy_s3_versioning_evidence(
    r: TerraformResource, legacy: Any, now: datetime
) -> Evidence:
    enabled_raw = legacy.get("enabled") if isinstance(legacy, dict) else None
    if isinstance(enabled_raw, list) and len(enabled_raw) == 1:
        enabled_raw = enabled_raw[0]
    enabled = enabled_raw is True or (
        isinstance(enabled_raw, str) and enabled_raw.strip().lower() == "true"
    )

    state = "present" if enabled else "absent"
    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
        "mechanism": "s3_versioning",
        "backup_state": state,
        "versioning_status": "Enabled" if enabled else "Disabled",
        "legacy_inline_block": True,
    }
    if not enabled:
        content["gap"] = (
            "legacy inline versioning block is disabled; object version "
            "history will not be retained"
        )

    return Evidence.create(
        detector_id="aws.backup_retention_configured",
        ksis_evidenced=["KSI-RPL-ABO"],
        controls_evidenced=["CP-9"],
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )
