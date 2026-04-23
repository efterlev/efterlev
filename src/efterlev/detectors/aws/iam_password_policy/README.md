# aws.iam_password_policy

Scans `aws_iam_account_password_policy` resources (a singleton per AWS
account) and compares the declared values to a FedRAMP Moderate
baseline. Emits one `Evidence` record per declared policy resource.

## Baseline thresholds

A policy is recorded as `posture=sufficient` when all seven of these
hold; `posture=weak` otherwise, with the specific shortfalls named
in the `gap` string.

| Setting | Threshold |
|---|---|
| `minimum_password_length` | ≥ 12 |
| `require_uppercase_characters` | `true` |
| `require_lowercase_characters` | `true` |
| `require_numbers` | `true` |
| `require_symbols` | `true` |
| `max_password_age` | ≤ 60 days |
| `password_reuse_prevention` | ≥ 24 |

## What it proves

- **IA-5 (Authenticator Management)** — an account-level password policy
  is declared with specific length, complexity, age, and reuse-prevention
  settings.
- **IA-5(1) (Password-Based Authentication)** — the password-specific
  enhancement, which names the four FedRAMP-era parameters above.

## What it does NOT prove

- **Per-user MFA enforcement.** That is the
  `mfa_required_on_iam_policies` detector's job. A strong password
  policy *plus* MFA is the baseline; this detector only evidences the
  password-policy half.
- **Password hashing, salt handling, PBKDF rounds at the IAM backend.**
  Those are AWS-internal operational concerns.
- **Procedural enforcement of forced resets** after incident response.
- **Runtime overrides.** Console changes are not captured.

## KSI mapping

**None.** Although IA-5 appears in KSI-IAM-MFA's `controls` array in
FRMR 0.9.43-beta, KSI-IAM-MFA's statement is specifically about
*phishing-resistant* MFA (FIDO2/WebAuthn tier, per CLAUDE.md's
detection-scope note). A password policy does not evidence MFA at all
— claiming KSI-IAM-MFA would be overclaiming, conflating "have password
requirements" with "enforce phishing-resistant MFA." Per DECISIONS
2026-04-21 design call #1 (Option C), the detector declares `ksis=[]`
and the Gap Agent renders findings at the 800-53 (IA-5) level only.

FRMR membership of a control in a KSI's `controls` array is necessary
but not sufficient for a detector to claim the KSI — the detector must
also actually evidence what the KSI's *statement* commits to.

## Example

Input:

```hcl
resource "aws_iam_account_password_policy" "strict" {
  minimum_password_length        = 14
  require_uppercase_characters   = true
  require_lowercase_characters   = true
  require_numbers                = true
  require_symbols                = true
  max_password_age               = 60
  password_reuse_prevention      = 24
}
```

Output:

```json
{
  "detector_id": "aws.iam_password_policy",
  "ksis_evidenced": [],
  "controls_evidenced": ["IA-5", "IA-5(1)"],
  "content": {
    "resource_type": "aws_iam_account_password_policy",
    "resource_name": "strict",
    "posture": "sufficient",
    "minimum_password_length": 14,
    "max_password_age": 60,
    "password_reuse_prevention": 24,
    "character_requirements": {
      "require_uppercase_characters": true,
      "require_lowercase_characters": true,
      "require_numbers": true,
      "require_symbols": true
    }
  }
}
```

## Fixtures

- `fixtures/should_match/` — policies meeting all baselines (`sufficient`).
- `fixtures/should_not_match/` — policies with at least one shortfall
  (`weak`), and .tf files with no password-policy resource.
