# aws.backup_retention_configured

Detects whether stateful AWS resources defined in Terraform have
backup mechanisms configured: a positive `backup_retention_period` on
RDS instances / clusters, or versioning enabled on S3 buckets (via
`aws_s3_bucket_versioning` or legacy inline `versioning` block).

## What this proves

- **KSI-RPL-ABO (Aligning Backups with Objectives), partial.** The
  backup mechanism is declared and active.
- **NIST SP 800-53 CP-9 (System Backup), partial.**

## What this does NOT prove

- **RTO/RPO alignment.** KSI-RPL-ABO's *alignment* claim requires a
  procedural argument (stated RTO/RPO, the backup config actually
  meets them, drill results). The scanner sees "retention=7 days" but
  not "the business needs 24-hour RPO."
- **Cross-region / cross-account replication.** A bucket with
  versioning is still a single blast-radius artifact; replication
  (e.g., `aws_s3_bucket_replication_configuration`) is a separate
  signal, deferred.
- **Restore-testing practices.** Backups that are never restored
  aren't demonstrably useful. Procedural evidence.
- **Backup integrity / encryption.** Backup snapshots inherit the
  source's encryption config in AWS; this detector doesn't re-verify.

## Evidence shape

See `evidence.yaml`. Each RDS / versioning resource produces one
Evidence record with `backup_state ∈ {present, absent}`. Absence of
any such resource produces no evidence — the Gap Agent classifies
the KSI as `not_implemented` from that zero-evidence state.
