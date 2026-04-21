"""AWS IAM policy MFA-required detector.

Evidences KSI-IAM-MFA ("Enforcing Phishing-Resistant MFA") and 800-53
IA-2 ("Identification and Authentication") at the infrastructure layer:
we confirm that IAM policy documents include a
`aws:MultiFactorAuthPresent` condition on `Allow` statements that would
otherwise grant sensitive access unconditionally.

Per CLAUDE.md's MVP scope note: this detector proves *MFA-presence*, not
*phishing-resistance*. KSI-IAM-MFA requires FIDO2/WebAuthn-tier MFA,
which lives in IdP configuration (Okta/Entra/Cognito) — procedural
evidence outside Terraform's view. The README names this gap explicitly.

Resource types inspected:
  - `aws_iam_policy`
  - `aws_iam_role_policy`
  - `aws_iam_user_policy`
  - `aws_iam_group_policy`

Evidence emitted per policy resource:
  - `mfa_required = "present"` — at least one `Allow` statement in the
    policy carries the `aws:MultiFactorAuthPresent=true` condition.
  - `mfa_required = "absent"`  — the policy has `Allow` statements but
    none of them require MFA.
  - `mfa_required = "unparseable"` — the `policy` attribute is a
    `jsonencode(...)`, `data.aws_iam_policy_document.*.json`, or other
    non-literal expression python-hcl2 cannot statically resolve. The
    Gap Agent treats this as partial rather than false-positive
    implemented.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.models import Evidence, TerraformResource

_IAM_POLICY_TYPES = {
    "aws_iam_policy",
    "aws_iam_role_policy",
    "aws_iam_user_policy",
    "aws_iam_group_policy",
}

_MFA_CONDITION_KEY = "aws:MultiFactorAuthPresent"


@detector(
    id="aws.mfa_required_on_iam_policies",
    ksis=["KSI-IAM-MFA"],
    controls=["IA-2"],
    source="terraform",
    version="0.1.0",
)
def detect(resources: list[TerraformResource]) -> list[Evidence]:
    """Emit MFA-state Evidence for every inspectable IAM policy resource.

    Evidences (KSI):     KSI-IAM-MFA (Enforcing Phishing-Resistant MFA) —
                         partial. Proves MFA presence, not phishing
                         resistance.
    Evidences (800-53):  IA-2 (Identification and Authentication).
    Does NOT prove:      (1) phishing resistance — that's an IdP-layer
                         concern (FIDO2/WebAuthn, hardware keys); (2)
                         policies produced via `aws_iam_policy_document`
                         data sources (we cannot statically resolve their
                         rendered JSON); (3) whether the policy is
                         actually attached to users/roles.
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)

    for r in resources:
        if r.type not in _IAM_POLICY_TYPES:
            continue
        out.append(_emit_policy_evidence(r, now))

    return out


def _emit_policy_evidence(r: TerraformResource, now: datetime) -> Evidence:
    policy_attr = r.body.get("policy")
    if isinstance(policy_attr, list) and len(policy_attr) == 1:
        policy_attr = policy_attr[0]

    policy_doc = _try_parse_policy(policy_attr)
    if policy_doc is None:
        return _evidence(
            r,
            now,
            mfa_required="unparseable",
            gap=(
                "policy attribute is not a literal JSON string "
                "(likely jsonencode or a data source reference); "
                "static analysis cannot determine MFA enforcement"
            ),
        )

    allow_statements = _allow_statements(policy_doc)
    if not allow_statements:
        # An IAM policy with no Allow statements doesn't grant anything to
        # enforce MFA on; treat as unparseable for classification purposes.
        return _evidence(
            r,
            now,
            mfa_required="unparseable",
            gap="policy has no Allow statements; nothing for MFA to gate",
        )

    has_mfa = any(_statement_requires_mfa(stmt) for stmt in allow_statements)
    if has_mfa:
        return _evidence(
            r,
            now,
            mfa_required="present",
            allow_count=len(allow_statements),
        )

    return _evidence(
        r,
        now,
        mfa_required="absent",
        allow_count=len(allow_statements),
        gap=(
            "policy grants Allow without an aws:MultiFactorAuthPresent condition on any statement"
        ),
    )


def _evidence(
    r: TerraformResource,
    now: datetime,
    *,
    mfa_required: str,
    allow_count: int | None = None,
    gap: str | None = None,
) -> Evidence:
    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
        "mfa_required": mfa_required,
    }
    if allow_count is not None:
        content["allow_statement_count"] = allow_count
    if gap is not None:
        content["gap"] = gap
    return Evidence.create(
        detector_id="aws.mfa_required_on_iam_policies",
        ksis_evidenced=["KSI-IAM-MFA"],
        controls_evidenced=["IA-2"],
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )


def _try_parse_policy(value: Any) -> dict[str, Any] | None:
    """Parse a `policy` attribute as JSON; return None if not a literal string."""
    if not isinstance(value, str):
        return None
    # python-hcl2 represents `jsonencode(...)` and interpolation references
    # as strings starting with "${" — those aren't parseable JSON.
    if value.strip().startswith("${"):
        return None
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _allow_statements(policy_doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Return every Allow statement dict in the policy, normalized to a list."""
    raw = policy_doc.get("Statement", [])
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [s for s in raw if isinstance(s, dict) and s.get("Effect") == "Allow"]


def _statement_requires_mfa(statement: dict[str, Any]) -> bool:
    """True iff `statement.Condition` references aws:MultiFactorAuthPresent=true."""
    condition = statement.get("Condition")
    if not isinstance(condition, dict):
        return False
    # Condition format: { "<operator>": { "<key>": <value> } }
    for operator_block in condition.values():
        if not isinstance(operator_block, dict):
            continue
        for key, value in operator_block.items():
            if key.lower() != _MFA_CONDITION_KEY.lower():
                continue
            # The value can be "true", True, or ["true"]. Accept any truthy
            # literal string that says so.
            if _is_true_literal(value):
                return True
    return False


def _is_true_literal(value: Any) -> bool:
    if isinstance(value, bool):
        return value is True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    if isinstance(value, list):
        return any(_is_true_literal(v) for v in value)
    return False
