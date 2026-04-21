# aws.encryption_s3_at_rest

Detects whether an S3 bucket declared in Terraform has server-side default
encryption configured. Emits one `Evidence` record per S3 bucket and per
standalone `aws_s3_bucket_server_side_encryption_configuration` resource.

## What it proves

- **SC-28 (Protection of Information at Rest)** — an S3 bucket defined in
  the scanned Terraform has (or does not have) a server-side encryption
  configuration at the bucket level.
- **SC-28(1) (Cryptographic Protection)** — additionally, when the
  configuration specifies a concrete `sse_algorithm`, evidence that a
  cryptographic method has been named.

## What it does NOT prove

- **Key management, rotation, BYOK practices.** Those are procedural
  (SC-12 territory) and require evidence the Terraform source cannot
  expose.
- **Bucket policy enforcement of encryption on writes.** This detector
  looks at the bucket's default-encryption configuration, not its bucket
  policy's `aws:SecureTransport` / `s3:x-amz-server-side-encryption`
  conditions.
- **Runtime state.** Already-deployed objects are not covered — only the
  declared configuration.
- **Whether a separate `aws_s3_bucket_server_side_encryption_configuration`
  resource covers an otherwise-unencrypted bucket.** The detector emits
  facts for each pattern independently. The Gap Agent (Phase 3) cross-
  references them.

## KSI mapping

**None.** Per DECISIONS 2026-04-21 (design call #1, Option C): FRMR
0.9.43-beta contains no KSI whose `controls` array lists SC-28, so this
detector declares `ksis=[]` rather than fudging a mapping to a KSI that
covers different semantic territory (KSI-SVC-VRI is SC-13 integrity, not
SC-28 confidentiality-at-rest). The Gap Agent renders findings from this
detector as "unmapped to any current KSI."

We expect this gap to resolve as FRMR matures. When it does, update the
`ksis:` list in both the `@detector` decorator and `mapping.yaml`.

## Example

Input (one `aws_s3_bucket` resource, encrypted):

```hcl
resource "aws_s3_bucket" "audit_logs" {
  bucket = "audit-logs-prod"
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "aws:kms"
      }
    }
  }
}
```

Output (one Evidence record):

```json
{
  "detector_id": "aws.encryption_s3_at_rest",
  "ksis_evidenced": [],
  "controls_evidenced": ["SC-28", "SC-28(1)"],
  "source_ref": {"file": "main.tf", "line_start": 1, "line_end": 10},
  "content": {
    "resource_type": "aws_s3_bucket",
    "resource_name": "audit_logs",
    "encryption_state": "present",
    "location": "inline",
    "algorithm": "aws:kms"
  }
}
```

## Fixtures

- `fixtures/should_match/` — `.tf` files expected to produce at least one
  Evidence record with `encryption_state=present`.
- `fixtures/should_not_match/` — `.tf` files expected to produce only
  negative-evidence records (`encryption_state=absent`) or no S3 resources.
