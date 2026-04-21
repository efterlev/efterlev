"""Default LLM client factory.

`get_default_client()` is the single entry point for agents. At v0 it
returns an `AnthropicClient`; the v1 Bedrock work adds a branch here
keyed on `EFTERLEV_LLM_BACKEND` (or similar) without touching any agent.
"""

from __future__ import annotations

from efterlev.llm.anthropic_client import AnthropicClient
from efterlev.llm.base import LLMClient

# CLAUDE.md: default model is claude-opus-4-7; switch to sonnet only for
# latency during demo. Agents can override per-call, but the default lives
# here so changing it is a one-line edit.
DEFAULT_MODEL = "claude-opus-4-7"


def get_default_client() -> LLMClient:
    """Return the default LLM client (Anthropic SDK at v0)."""
    return AnthropicClient()
