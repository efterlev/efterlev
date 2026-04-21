"""Centralized LLM client layer.

Per CLAUDE.md: every `anthropic.Anthropic()` instantiation goes through
`get_default_client()` so the v1 pluggable-backend work (AWS Bedrock as
the second backend) is a drop-in rather than a scatter-rewrite. Agents
import `LLMClient` and `get_default_client`; they never import
`anthropic` directly.

At v0 the only backend is the Anthropic SDK over its native API. The
`LLMClient` protocol is narrow on purpose — just the call shape every
agent needs (system prompt + user prompt + structured response hooks) —
to keep the Bedrock adapter small when it lands.
"""

from __future__ import annotations

from efterlev.llm.base import LLMClient, LLMMessage, LLMResponse, StubLLMClient
from efterlev.llm.factory import DEFAULT_MODEL, get_default_client

__all__ = [
    "DEFAULT_MODEL",
    "LLMClient",
    "LLMMessage",
    "LLMResponse",
    "StubLLMClient",
    "get_default_client",
]
