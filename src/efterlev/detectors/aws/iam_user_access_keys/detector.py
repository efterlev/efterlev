"""IAM user long-lived access-keys detector.

Scans `aws_iam_access_key` resources. In a FedRAMP-authorized boundary,
long-lived programmatic access keys are a posture gap: the expected
pattern is federated identity (IAM Identity Center / OIDC federation
with MFA enforced at the IdP), or workload-to-workload authentication
via IAM roles assumed by AWS services (EC2 instance profiles, ECS
task roles, GitHub Actions OIDC, Lambda execution roles). Any
declared `aws_iam_access_key` is a deliberate opt-out of that pattern
and should be named in the attestation.

KSI mapping: this detector claims KSI-IAM-MFA despite not directly
evidencing MFA. The discipline from DECISIONS 2026-04-22 "Phase 6-lite"
says control membership is necessary but not sufficient — the detector
must also evidence what the KSI's *statement* commits to. KSI-IAM-MFA's
statement is about enforcing phishing-resistant MFA for user
authentication. A long-lived programmatic access key is a credential
that bypasses MFA by design: whoever holds the secret authenticates
without an IdP challenge. The detector therefore materially evidences
a posture question the KSI commits to (is MFA actually enforced for
every access path?), and the claim is honest. Contrast with
`iam_password_policy`, which only evidences password strength — not
MFA at all — and declares `ksis=[]`.

Motivated by the 2026-04-22 dogfood pass: ground-truth gap #8
(govnotes `ci_deploy` IAM user with long-lived keys) was invisible
without this detector.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.models import Evidence, TerraformResource


@detector(
    id="aws.iam_user_access_keys",
    ksis=["KSI-IAM-MFA"],
    controls=["IA-2", "AC-2"],
    source="terraform",
    version="0.1.0",
)
def detect(resources: list[TerraformResource]) -> list[Evidence]:
    """Emit access-key Evidence for every aws_iam_access_key found.

    Evidences (800-53):  IA-2 (Identification and Authentication),
                         AC-2 (Account Management) — a long-lived
                         programmatic credential is declared for an IAM
                         user.
    Evidences (KSI):     KSI-IAM-MFA — access keys bypass MFA by
                         design; their presence is material to whether
                         the boundary actually enforces MFA for every
                         authentication path.
    Does NOT prove:      whether the key is actually used in
                         production, key rotation cadence (AWS IAM
                         does not natively rotate access keys —
                         rotation is procedural), whether the
                         attached user also requires MFA for console
                         access (orthogonal), or whether a federated
                         alternative is in flight (procedural).
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)

    for r in resources:
        if r.type != "aws_iam_access_key":
            continue
        out.append(_emit_access_key_evidence(r, now))
    return out


def _emit_access_key_evidence(r: TerraformResource, now: datetime) -> Evidence:
    body = r.body
    user_ref = body.get("user")
    user_str = user_ref if isinstance(user_ref, str) else None

    status = body.get("status")
    # Default in AWS is "Active"; an explicit "Inactive" is still a
    # declared key (the secret exists in state and can be re-enabled).
    status_str = status if isinstance(status, str) and status else "Active"

    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
        "attached_user": user_str,
        "status": status_str,
        "gap": (
            "long-lived programmatic access key declared; "
            "prefer IAM role with federated identity or workload assumption"
        ),
    }
    # Record any in-band wrapping of the secret (PGP, ssh_public_key)
    # so the Gap Agent can note that the secret isn't just stored in
    # plaintext Terraform state. Doesn't change the gap, but matters
    # for the narrative.
    if body.get("pgp_key"):
        content["secret_wrapping"] = "pgp"
    elif body.get("ssh_public_key"):
        content["secret_wrapping"] = "ssh_public_key"

    return Evidence.create(
        detector_id="aws.iam_user_access_keys",
        ksis_evidenced=["KSI-IAM-MFA"],
        controls_evidenced=["IA-2", "AC-2"],
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )
