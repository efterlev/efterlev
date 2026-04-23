# aws.cloudtrail_log_file_validation

Scans `aws_cloudtrail` resources for the `enable_log_file_validation`
flag. AWS writes a per-hour digest file that a 3PAO can later use to
prove the log files weren't tampered with post-delivery. This is the
integrity-of-audit-logs concern (AU-9), orthogonal to the event-coverage
concern covered by the existing `cloudtrail_audit_logging` detector.

## What it proves

- **AU-9 (Protection of Audit Information)** — a CloudTrail trail
  declares AWS's native log-file-integrity-validation mechanism.

## What it does NOT prove

- **Downstream SIEM integrity preservation.** If logs are re-indexed
  into Splunk / Elastic / SumoLogic / Datadog, the AWS digest may not
  be carried through. Procedural controls — not our territory.
- **Periodic validation exercises.** AWS provides the validation data;
  SOC operations must periodically run `aws cloudtrail validate-logs`
  to actually verify it.
- **S3 object-lock posture on the CloudTrail bucket.** Without object-
  lock / versioning the digest is moot (an attacker with delete access
  can remove both the logs and the digest). That's the
  `backup_retention_configured` detector's adjacency; the Gap Agent
  cross-references.
- **Runtime state.** Only the Terraform declaration is examined.

## KSI mapping

**KSI-MLA-OSM (Operating SIEM Capability).** FRMR 0.9.43-beta lists au-9
in this KSI's `controls` array, and its statement explicitly calls out
"tamper-resistant logging." Clean, direct mapping.

## Relationship to `cloudtrail_audit_logging`

The two CloudTrail detectors scan the same resources but cover different
controls:

| Detector | Controls | Concern |
|---|---|---|
| `cloudtrail_audit_logging` | AU-2, AU-12 | What is logged (event selectors, multi-region) |
| `cloudtrail_log_file_validation` | AU-9 | Integrity of the log files themselves |

Both emit Evidence per trail; the Gap Agent composes them.

## Example

Input:

```hcl
resource "aws_cloudtrail" "main" {
  name                          = "main-trail"
  s3_bucket_name                = "audit-logs-bucket"
  is_multi_region_trail         = true
  include_global_service_events = true
  enable_log_file_validation    = true
}
```

Output:

```json
{
  "detector_id": "aws.cloudtrail_log_file_validation",
  "ksis_evidenced": ["KSI-MLA-OSM"],
  "controls_evidenced": ["AU-9"],
  "content": {
    "resource_type": "aws_cloudtrail",
    "resource_name": "main",
    "validation_status": "enabled"
  }
}
```

## Fixtures

- `fixtures/should_match/` — trails with `enable_log_file_validation=true`.
- `fixtures/should_not_match/` — trails with it unset/false, and .tf
  files with no `aws_cloudtrail` resources.
