# aws.s3_public_access_block

Detects `aws_s3_bucket_public_access_block` resources and reports whether
each one sets all four bucket-level public-access-restriction flags to
`true`. Emits one `Evidence` record per PAB resource.

## What it proves

- **AC-3 (Access Enforcement)** — a bucket-level public-access-block
  resource is declared and its per-flag posture is visible in Terraform.
  Four flags are checked: `block_public_acls`, `ignore_public_acls`,
  `block_public_policy`, `restrict_public_buckets`.

## What it does NOT prove

- **That every bucket in the repo is covered by a PAB resource.** Some
  buckets may have no PAB at all (the riskier configuration). The Gap
  Agent cross-references buckets↔PAB resources at reasoning time.
- **That the applied bucket policies don't themselves grant public
  access.** PAB restricts but does not fully preclude a permissive
  bucket policy in every case; the policy itself must be inspected.
- **The account-level PAB setting.** AWS also supports
  account-wide public access blocking (via
  `aws_s3_account_public_access_block`). That is not declared by
  typical bucket-level Terraform and requires separate evidence.
- **Runtime state.** Deployed buckets' actual posture may differ from
  what the Terraform declares — only the declaration is examined.

## KSI mapping

**None.** Per DECISIONS 2026-04-21 (design call #1, Option C): FRMR
0.9.43-beta contains no KSI whose `controls` array lists AC-3, so this
detector declares `ksis=[]` rather than fudging a mapping. Claiming
KSI-SVC-VRI (which centers on SC-13 integrity) would conflate different
semantic territory.

## Example

Input:

```hcl
resource "aws_s3_bucket_public_access_block" "private" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}
```

Output (one Evidence record):

```json
{
  "detector_id": "aws.s3_public_access_block",
  "ksis_evidenced": [],
  "controls_evidenced": ["AC-3"],
  "content": {
    "resource_type": "aws_s3_bucket_public_access_block",
    "resource_name": "private",
    "posture": "fully_blocked",
    "flags": {
      "block_public_acls": true,
      "ignore_public_acls": true,
      "block_public_policy": true,
      "restrict_public_buckets": true
    }
  }
}
```

## Fixtures

- `fixtures/should_match/` — PAB resources with all four flags true
  (`posture=fully_blocked`).
- `fixtures/should_not_match/` — PAB resources with at least one flag
  false or absent (`posture=partial`) and .tf files with no PAB resources.
