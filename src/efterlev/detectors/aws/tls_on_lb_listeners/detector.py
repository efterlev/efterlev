"""AWS Load Balancer listener TLS-in-transit detector.

Evidences KSI-SVC-SNT ("Securing Network Traffic") and 800-53 SC-8
("Transmission Confidentiality and Integrity") at the infrastructure
layer: we confirm that `aws_lb_listener` / `aws_alb_listener` blocks
accept connections over HTTPS/TLS with a certificate attached, not
plain HTTP/TCP.

Evidence emitted per listener:
  - `tls_state = "present"` when `protocol` is HTTPS or TLS.
  - `tls_state = "absent"` when `protocol` is HTTP or TCP.
  - `ssl_policy` (string) and `certificate_arn_present` (bool) are
    included for TLS listeners so downstream tooling (Documentation
    Agent, possible FIPS-policy follow-up detector) can reason about
    the cipher choice without re-parsing.

Per CLAUDE.md scope: this proves the listener accepts TLS; it does not
prove (a) redirects from HTTP to HTTPS are configured, (b) the ssl_policy
is FIPS-approved — that's a separate check, deferred, (c) certificates
are rotated, valid, or bound to the right hostnames (runtime concerns).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from efterlev.detectors.base import detector
from efterlev.models import Evidence, TerraformResource

_TLS_PROTOCOLS = {"HTTPS", "TLS"}
_PLAIN_PROTOCOLS = {"HTTP", "TCP", "UDP", "TCP_UDP"}

_LISTENER_TYPES = {"aws_lb_listener", "aws_alb_listener"}


@detector(
    id="aws.tls_on_lb_listeners",
    ksis=["KSI-SVC-SNT"],
    controls=["SC-8"],
    source="terraform",
    version="0.1.0",
)
def detect(resources: list[TerraformResource]) -> list[Evidence]:
    """Emit TLS-state Evidence for every LB listener.

    Evidences (KSI):     KSI-SVC-SNT (Securing Network Traffic) — partial.
                         Infrastructure layer only.
    Evidences (800-53):  SC-8 (Transmission Confidentiality and Integrity).
    Does NOT prove:      HTTP→HTTPS redirects; FIPS-compliance of the
                         ssl_policy (see the follow-up crypto-protection
                         detector); certificate rotation or validity;
                         runtime cipher negotiation outcomes.
    """
    out: list[Evidence] = []
    now = datetime.now(UTC)

    for r in resources:
        if r.type not in _LISTENER_TYPES:
            continue
        out.append(_emit_listener_evidence(r, now))

    return out


def _emit_listener_evidence(r: TerraformResource, now: datetime) -> Evidence:
    protocol = _as_str(r.body.get("protocol"))
    port = r.body.get("port")
    ssl_policy = _as_str(r.body.get("ssl_policy"))
    cert_arn = _as_str(r.body.get("certificate_arn"))

    if protocol and protocol.upper() in _TLS_PROTOCOLS:
        tls_state = "present"
    elif protocol and protocol.upper() in _PLAIN_PROTOCOLS:
        tls_state = "absent"
    else:
        # Protocol absent or unrecognized — treat as "unknown" rather than
        # claiming presence or absence. The Gap Agent sees this as partial.
        tls_state = "unknown"

    content: dict[str, Any] = {
        "resource_type": r.type,
        "resource_name": r.name,
        "protocol": protocol,
        "port": port,
        "tls_state": tls_state,
        "certificate_arn_present": bool(cert_arn),
    }
    if ssl_policy is not None:
        content["ssl_policy"] = ssl_policy
    if tls_state == "absent":
        content["gap"] = (
            f"listener protocol is {protocol!r}; traffic to this listener "
            "is not encrypted in transit"
        )

    return Evidence.create(
        detector_id="aws.tls_on_lb_listeners",
        ksis_evidenced=["KSI-SVC-SNT"],
        controls_evidenced=["SC-8"],
        source_ref=r.source_ref,
        content=content,
        timestamp=now,
    )


def _as_str(value: Any) -> str | None:
    """python-hcl2 occasionally returns strings wrapped in single-element lists."""
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    return value if isinstance(value, str) else None
