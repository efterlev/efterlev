# aws.cloudtrail_audit_logging

Detects whether an `aws_cloudtrail` resource exists and is configured
for broad management-event coverage (multi-region + global service
events).

## What this proves

- **KSI-MLA-LET (Logging Event Types), partial.** A CloudTrail trail
  is declared; management events are captured across regions when
  both `is_multi_region_trail = true` and
  `include_global_service_events = true`.
- **KSI-MLA-OSM (Operating SIEM Capability), partial.** The SIEM ingest
  surface (CloudTrail → S3 / EventBridge) exists.
- **NIST SP 800-53 AU-2 (Event Logging), partial.**
- **NIST SP 800-53 AU-12 (Audit Record Generation), partial.**

## What this does NOT prove

- **Downstream SIEM ingestion or alerting.** CloudTrail events may land
  in S3 but never reach Splunk / a SIEM / a human. The integration is
  outside the scanner's view.
- **Log retention.** CloudTrail's S3 destination bucket's lifecycle
  policy determines retention. This detector doesn't inspect that.
- **Log-file validation / CloudTrail Lake.** Integrity guarantees
  (AU-9) need a separate detector (v1).
- **Data-event coverage.** Management events are the default; data
  events (S3 object reads, Lambda invocations) require explicit
  `event_selector` blocks. We flag whether any event_selector exists
  but don't enforce coverage beyond management events.

## Evidence shape

See `evidence.yaml`. Each `aws_cloudtrail` resource produces one
Evidence record with `cloudtrail_state ∈ {present, partial}`. Absence
of any CloudTrail resource produces no evidence — the Gap Agent
classifies the KSI as `not_implemented` from that zero-evidence state.
