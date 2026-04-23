"""IAM account password-policy detector.

Scans `aws_iam_account_password_policy` resources. The resource is a
singleton per AWS account — `terraform apply` replaces the account-level
policy wholesale. The detector records the declared values and flags any
value weaker than the FedRAMP Moderate baseline (IA-5(1) guidance):

  - minimum_password_length     >= 12
  - require_uppercase_characters = true
  - require_lowercase_characters = true
  - require_numbers              = true
  - require_symbols              = true
  - max_password_age             <= 60 (days)
  - password_reuse_prevention    >= 24

A resource meeting all seven emits `posture=sufficient`. Any shortfall
emits `posture=weak` with a `gap` string naming the specific fields.

Per DECISIONS 2026-04-21 design call #1, Option C: this detector does
NOT claim KSI-IAM-MFA. That KSI is specifically about *phishing-resistant
MFA* (FIDO2/WebAuthn tier per CLAUDE.md's detection-scope note). A
password policy does not evidence MFA at all — claiming KSI-IAM-MFA
would be overclaiming. IA-5 is in KSI-IAM-MFA's control array in FRMR,
but that does not transitively license the mapping; control membership
is necessary, not sufficient. The detector declares `ksis=[]` and
surfaces at the 800-53 level only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.models import Evidence, TerraformResource

_REQUIRED_CHAR_FLAGS = (
    "require_uppercase_characters",
    "require_lowercase_characters",
    "require_numbers",
    "require_symbols",
)
_MIN_LENGTH = 12
_MAX_AGE_DAYS = 60
_REUSE_PREVENTION = 24


@detector(
    id="aws.iam_password_policy",
    ksis=[],  # DECISIONS 2026-04-21: password policy ≠ phishing-resistant MFA
    controls=["IA-5", "IA-5(1)"],
    source="terraform",
    version="0.1.0",
)
def detect(resources: list[TerraformResource]) -> list[Evidence]:
    """Emit password-policy Evidence for every aws_iam_account_password_policy found.

    Evidences (800-53):  IA-5 (Authenticator Management), IA-5(1)
                         (Password-Based Authentication) — the declared
                         account-level password policy is visible.
    Evidences (KSI):     None — password policy is IA-5 territory, not
                         KSI-IAM-MFA (which is about phishing-resistant
                         MFA). See detector README.
    Does NOT prove:      per-user MFA enforcement (that is the
                         `mfa_required_on_iam_policies` detector's job);
                         password hashing algorithms at the IAM backend;
                         procedural enforcement of password resets;
                         runtime state (console overrides).
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)

    for r in resources:
        if r.type != "aws_iam_account_password_policy":
            continue
        out.append(_emit_policy_evidence(r, now))
    return out


def _emit_policy_evidence(r: TerraformResource, now: datetime) -> Evidence:
    body = r.body

    min_length = _coerce_int(body.get("minimum_password_length"))
    max_age = _coerce_int(body.get("max_password_age"))
    reuse_prev = _coerce_int(body.get("password_reuse_prevention"))
    char_flags = {flag: _coerce_bool(body.get(flag)) for flag in _REQUIRED_CHAR_FLAGS}

    gaps: list[str] = []
    if min_length is None or min_length < _MIN_LENGTH:
        gaps.append(f"minimum_password_length < {_MIN_LENGTH}")
    for flag, value in char_flags.items():
        if value is not True:
            gaps.append(f"{flag} not true")
    if max_age is None or max_age > _MAX_AGE_DAYS:
        gaps.append(f"max_password_age > {_MAX_AGE_DAYS}")
    if reuse_prev is None or reuse_prev < _REUSE_PREVENTION:
        gaps.append(f"password_reuse_prevention < {_REUSE_PREVENTION}")

    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
        "posture": "sufficient" if not gaps else "weak",
        "minimum_password_length": min_length,
        "max_password_age": max_age,
        "password_reuse_prevention": reuse_prev,
        "character_requirements": char_flags,
    }
    if gaps:
        content["gap"] = "; ".join(gaps)

    return Evidence.create(
        detector_id="aws.iam_password_policy",
        ksis_evidenced=[],
        controls_evidenced=["IA-5", "IA-5(1)"],
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _coerce_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None
