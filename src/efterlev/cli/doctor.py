"""`efterlev doctor` — self-diagnose pre-flight checks.

Priority 3 (2026-04-28). On a fresh install, the most-common failure
mode is "agent invocation explodes because ANTHROPIC_API_KEY is unset"
or "FRMR cache is missing because init wasn't run." Both produce
unfriendly tracebacks. `efterlev doctor` runs a series of cheap checks
and reports per-check pass/fail with remediation pointers, so users
catch the misconfiguration before the first agent run.

Checks are pure functions that return a `Check` dataclass. The
top-level `run_doctor_checks(target)` aggregates them. The CLI command
in `cli/main.py` wires it to typer and exits non-zero if any required
check fails.

Network reachability checks are intentionally NOT included — they're
flaky in CI sandboxes, add latency, and add a network dependency to a
diagnostic tool. The doctor inspects local state only.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CheckStatus = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class Check:
    """One diagnostic check's outcome.

    `severity`: a "fail" indicates the user can't run the agent
    pipeline — exit non-zero. A "warn" is a heads-up (e.g. Bedrock
    creds optional, FRMR cache slightly stale). A "pass" is the green
    case.
    """

    name: str
    status: CheckStatus
    detail: str
    hint: str | None = None


# Minimum supported Python — matches pyproject.toml's `requires-python`.
_MIN_PYTHON = (3, 10)


def check_python_version() -> Check:
    if sys.version_info[:2] >= _MIN_PYTHON:
        return Check(
            name="python_version",
            status="pass",
            detail=f"Python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}",
        )
    cur_v = f"{sys.version_info[0]}.{sys.version_info[1]}"
    min_v = f"{_MIN_PYTHON[0]}.{_MIN_PYTHON[1]}"
    return Check(
        name="python_version",
        status="fail",
        detail=f"Python {cur_v} is below required {min_v}",
        hint="Upgrade Python to 3.10 or newer (we recommend 3.12).",
    )


def check_anthropic_api_key() -> Check:
    """Check ANTHROPIC_API_KEY presence and shape.

    The shape check is conservative: real keys start with `sk-ant-`
    and are 100+ chars. We don't make a network call to validate the
    key — that's a separate concern from "is it configured."
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return Check(
            name="anthropic_api_key",
            status="warn",
            detail="ANTHROPIC_API_KEY is not set in the environment",
            hint=(
                "Set ANTHROPIC_API_KEY before running any `efterlev agent` "
                "command. Get a key at https://console.anthropic.com. "
                "Bedrock users can skip this — see `[bedrock]` in config.toml."
            ),
        )
    if not key.startswith("sk-ant-"):
        return Check(
            name="anthropic_api_key",
            status="warn",
            detail=f"ANTHROPIC_API_KEY is set but doesn't start with 'sk-ant-' (length {len(key)})",
            hint=(
                "Real Anthropic API keys start with `sk-ant-`. The current "
                "value may be a Bedrock key or a leftover placeholder. "
                "Verify before running an agent."
            ),
        )
    return Check(
        name="anthropic_api_key",
        status="pass",
        detail=f"ANTHROPIC_API_KEY is set (sk-ant-…, length {len(key)})",
    )


def check_efterlev_dir(target: Path) -> Check:
    """Check whether `.efterlev/` exists in the target directory."""
    efterlev_dir = target / ".efterlev"
    if efterlev_dir.is_dir():
        return Check(
            name="efterlev_dir",
            status="pass",
            detail=f".efterlev/ found at {efterlev_dir}",
        )
    return Check(
        name="efterlev_dir",
        status="warn",
        detail=f"No .efterlev/ at {target} — workspace not initialized",
        hint="Run `efterlev init` in the workspace before scanning or invoking agents.",
    )


_FRMR_CACHE_REL = Path(".efterlev/cache/frmr_document.json")
# Stale threshold: 90 days. The FRMR catalog is vendored, so the cache
# is the canonical local copy — if it's older than this, the user is
# almost certainly running against an outdated FedRAMP standard.
_FRMR_STALE_SECONDS = 90 * 24 * 60 * 60


def check_frmr_cache(target: Path) -> Check:
    """Check the FRMR-cache file is present and not impossibly stale."""
    cache = target / _FRMR_CACHE_REL
    if not cache.is_file():
        return Check(
            name="frmr_cache",
            status="warn",
            detail=f"FRMR cache missing at {cache}",
            hint=(
                "Run `efterlev init` to populate the FRMR cache. The "
                "cache contains the vendored FedRAMP catalog; agents "
                "and `efterlev scan` need it."
            ),
        )
    age_seconds = time.time() - cache.stat().st_mtime
    if age_seconds > _FRMR_STALE_SECONDS:
        days = int(age_seconds / 86400)
        return Check(
            name="frmr_cache",
            status="warn",
            detail=f"FRMR cache at {cache} is {days} days old",
            hint=(
                "Re-run `efterlev init --force` to refresh the FRMR "
                "cache from the vendored catalog (which itself ships "
                "with the installed efterlev package)."
            ),
        )
    return Check(
        name="frmr_cache",
        status="pass",
        detail=f"FRMR cache at {cache}",
    )


def check_bedrock_credentials() -> Check:
    """Optional check: is the Bedrock LLM backend usable?

    AWS_REGION + AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY (or an
    AWS_PROFILE) is the canonical signal. We don't validate the keys
    actually work — that's a network call. Pass = "Bedrock is plausibly
    configured"; warn = "Bedrock not configured" (which is fine if the
    user is on the Anthropic backend).
    """
    has_env_creds = bool(
        os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")
    )
    has_profile = bool(os.environ.get("AWS_PROFILE"))
    has_region = bool(os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"))

    if not (has_env_creds or has_profile):
        return Check(
            name="bedrock_credentials",
            status="warn",
            detail="No AWS credentials in environment (Bedrock backend unavailable)",
            hint=(
                "If you don't use Bedrock, ignore this check. To enable "
                "Bedrock: set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY "
                "(or AWS_PROFILE) plus AWS_REGION, then set "
                "[llm].backend = 'bedrock' in .efterlev/config.toml."
            ),
        )
    if not has_region:
        return Check(
            name="bedrock_credentials",
            status="warn",
            detail="AWS credentials present but AWS_REGION not set",
            hint="Set AWS_REGION (or AWS_DEFAULT_REGION) so Bedrock knows where to call.",
        )
    return Check(
        name="bedrock_credentials",
        status="pass",
        detail="AWS credentials + AWS_REGION present (Bedrock backend usable)",
    )


def run_doctor_checks(target: Path) -> list[Check]:
    """Run every doctor check and return the results in display order.

    Order: Python (foundational), .efterlev workspace state, FRMR cache
    (init artifact), API keys (agent invocation), Bedrock (optional).
    """
    return [
        check_python_version(),
        check_efterlev_dir(target),
        check_frmr_cache(target),
        check_anthropic_api_key(),
        check_bedrock_credentials(),
    ]


def has_failures(checks: list[Check]) -> bool:
    """True if any check is `fail` (the gate for non-zero exit). Warns
    don't block — they're informational."""
    return any(c.status == "fail" for c in checks)
