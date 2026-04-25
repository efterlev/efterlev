#!/usr/bin/env bash
# Pre-flip grep-scrub. Run before flipping the repo from private to
# public per SPEC-56.1. Greps for NDA-era language, stale URL
# references, secret-shaped strings that snuck past the redaction
# library at commit time.
#
# Exit 0 = clean OR all findings allowlisted.
# Exit 1 = at least one un-allowlisted finding; review each and either
#          fix or add to the allowlist with rationale.
#
# Allowlist entries live in scripts/launch-grep-scrub.allowlist (one
# regex per line, anchored against `<file>:<line>:<text>` shape).

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

ALLOWLIST_FILE="scripts/launch-grep-scrub.allowlist"
EXIT_CODE=0

# Build a single composite regex of allowlist entries (or a no-op if
# the file is missing).
ALLOWLIST_REGEX=""
if [ -f "$ALLOWLIST_FILE" ]; then
  # Filter out comment lines and empty lines.
  ALLOWLIST_REGEX="$(grep -vE '^\s*(#|$)' "$ALLOWLIST_FILE" | tr '\n' '|' | sed 's/|$//')"
fi

run_check() {
  local name="$1"
  local pattern="$2"
  local description="$3"
  local extra_flags="${4:-}"

  echo "=== $name ==="
  echo "$description"
  echo

  # Search tracked files only; -I skips binaries; -n adds line numbers.
  # `extra_flags` lets a check pass `-i` for case-insensitive matching.
  local raw
  raw="$(git grep $extra_flags -I -n -E "$pattern" -- ':!scripts/launch-grep-scrub.sh' ':!scripts/launch-grep-scrub.allowlist' || true)"

  if [ -z "$raw" ]; then
    echo "  ✓ no matches"
    echo
    return 0
  fi

  # Apply allowlist if present.
  local filtered
  if [ -n "$ALLOWLIST_REGEX" ]; then
    filtered="$(echo "$raw" | grep -vE "$ALLOWLIST_REGEX" || true)"
  else
    filtered="$raw"
  fi

  if [ -z "$filtered" ]; then
    echo "  ✓ all matches allowlisted"
    echo
    return 0
  fi

  echo "$filtered" | sed 's/^/  ✗ /'
  echo
  EXIT_CODE=1
}

# --- 1. NDA-era / closed-source-era language ---------------------------------

run_check "nda_language" \
  '\bNDA\b|under NDA|customer security review under NDA|closed-NDA' \
  "Forbidden: explicit NDA references. The closed-source-through-v1 lock was rescinded 2026-04-23."

run_check "closed_source_status_language" \
  'closed-source through v1|closed-development|external contributions paused|v1 public-repo opening' \
  "Forbidden: status-line claims that the project is still closed."

run_check "private_repo_language" \
  'private GitHub repo|repo is currently private|private-repo invite|private-repo-under-NDA' \
  "Forbidden: explicit 'private repo' framing in user-facing docs."

# --- 2. Stale URL / repo-name references --------------------------------------

run_check "lhassa8_repo_references" \
  'github\.com/lhassa8/[Ee]fterlev|lhassa8/Efterlev|lhassa8/efterlev' \
  "Forbidden: references to the pre-transfer repo name. Should be efterlev/efterlev."

# --- 3. Secret-shaped strings (defense in depth at git-history-time) ----------

run_check "aws_access_key_shape" \
  '\bAKIA[0-9A-Z]{16}\b' \
  "Forbidden: AWS access key IDs in the repo. The runtime scrubber catches these in LLM prompts; this catch is for committed strings."

run_check "anthropic_key_shape" \
  '\bsk-ant-[A-Za-z0-9_-]{20,}' \
  "Forbidden: Anthropic API key prefix in committed files."

run_check "github_token_shape" \
  '\b(ghp_|gho_|ghs_|github_pat_)[A-Za-z0-9_]{36,}' \
  "Forbidden: GitHub token prefix in committed files."

run_check "pem_private_key" \
  '-----BEGIN ([A-Z]+ )?PRIVATE KEY-----' \
  "Forbidden: PEM private key blocks in committed files."

# --- 4. Stale internal-status language ----------------------------------------

run_check "stale_test_count" \
  '344 passing|279 passing|461 passing|496 passing|529 passing|552 passing' \
  "Forbidden: stale test counts. Use the current count from \`uv run pytest -m 'not e2e'\`."

run_check "internal_only_markers" \
  '(internal only|do not distribute|confidential)' \
  "Forbidden: internal-only / DND / confidential markers." \
  "-i"

# --- summary ------------------------------------------------------------------

if [ $EXIT_CODE -eq 0 ]; then
  echo "RESULT: clean. Repo passes pre-flip grep-scrub."
else
  echo "RESULT: findings present. Review each, fix or allowlist with rationale."
  echo "        Allowlist file: $ALLOWLIST_FILE"
fi

exit $EXIT_CODE
