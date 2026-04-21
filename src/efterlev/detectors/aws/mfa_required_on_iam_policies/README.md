# aws.mfa_required_on_iam_policies

Detects whether inline or managed IAM policy documents defined in
Terraform (`aws_iam_policy`, `aws_iam_role_policy`, `aws_iam_user_policy`,
`aws_iam_group_policy`) gate `Allow` statements behind the
`aws:MultiFactorAuthPresent` condition.

## What this proves

- **KSI-IAM-MFA (Enforcing Phishing-Resistant MFA), partial.** The
  policy grants privileged actions only when the caller's session was
  established with MFA.
- **NIST SP 800-53 IA-2 (Identification and Authentication), partial.**
  Infrastructure-layer evidence — IAM policy text requires MFA.

## What this does NOT prove

- **Phishing resistance.** KSI-IAM-MFA's "phishing-resistant" qualifier
  means FIDO2/WebAuthn/hardware-key factor. The detector proves
  *MFA-presence*, not that the MFA factor is phishing-resistant. That
  sits in the IdP configuration layer (Okta, Entra, Cognito) and is
  procedural evidence beyond Terraform's view.
- **Policy attachment.** A policy with MFA conditions is only useful if
  it's actually attached to a user, role, or group. This detector
  inspects policy *documents*, not attachments.
- **Policies rendered via data sources.** Policies built with
  `aws_iam_policy_document` data sources or `jsonencode(...)` produce
  `mfa_required="unparseable"` evidence since static analysis can't see
  the rendered JSON. The Gap Agent treats this as partial.
- **Non-IAM MFA enforcement.** Service-level MFA (e.g., S3 bucket
  policies, MFA-delete on versioned buckets) is a separate signal not
  covered here.

## Evidence shape

See `evidence.yaml`. Each IAM policy resource produces one Evidence
record with `mfa_required ∈ {present, absent, unparseable}`.
