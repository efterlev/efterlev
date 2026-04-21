"""Anthropic SDK adapter for `LLMClient`.

Thin wrapper over `anthropic.Anthropic`. Lazy SDK import so the package
imports cleanly in environments without the SDK available (tests that
stub out LLM calls entirely, minimal CI, etc.).
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from efterlev.errors import AgentError
from efterlev.llm.base import LLMMessage, LLMResponse

if TYPE_CHECKING:  # pragma: no cover
    from anthropic import Anthropic

log = logging.getLogger(__name__)


@dataclass
class AnthropicClient:
    """`LLMClient`-shaped wrapper over the Anthropic Python SDK."""

    api_key: str | None = None
    _sdk: Any = field(default=None, init=False, repr=False)

    def _client(self) -> Anthropic:
        if self._sdk is None:
            try:
                from anthropic import Anthropic
            except ImportError as e:  # pragma: no cover - guard
                raise AgentError(
                    "anthropic SDK not installed; install `anthropic` or inject a StubLLMClient"
                ) from e
            key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise AgentError(
                    "ANTHROPIC_API_KEY is not set. Export it, or inject a StubLLMClient."
                )
            self._sdk = Anthropic(api_key=key)
        return self._sdk  # type: ignore[no-any-return]

    def complete(
        self,
        *,
        system: str,
        messages: list[LLMMessage],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        joined = system + "\n".join(m.content for m in messages)
        prompt_hash = hashlib.sha256(joined.encode("utf-8")).hexdigest()

        client = self._client()
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": m.content} for m in messages],
            )
        except Exception as e:
            raise AgentError(f"anthropic completion failed: {e}") from e

        # SDK returns a list of content blocks; only `text` blocks are expected
        # for these agents. Concatenate if the model chunked the response.
        parts: list[str] = []
        for block in resp.content:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(text)
        if not parts:
            raise AgentError(
                f"anthropic response had no text content (stop_reason={resp.stop_reason!r})"
            )
        return LLMResponse(text="".join(parts), model=resp.model, prompt_hash=prompt_hash)
