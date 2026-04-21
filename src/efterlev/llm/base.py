"""LLM client protocol + a stub for tests.

`LLMClient` is the minimal call shape every Efterlev agent needs. The
Anthropic v0 implementation lives in `anthropic_client.py`; the Bedrock
v1 implementation will land alongside it behind the same protocol.

`StubLLMClient` is the fixture every agent test uses — it returns canned
responses without hitting the network and records the last prompt so
tests can assert on prompt shape (XML fencing, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMMessage:
    """One user-role message to an LLM. Role is implicit at v0: always 'user'."""

    content: str


@dataclass(frozen=True)
class LLMResponse:
    """LLM output paired with the metadata agents need for provenance.

    `model` is the exact model identifier the backend served (not the
    requested alias), so provenance records can pin the responding model.
    `prompt_hash` is the sha256 of `system + messages` as sent; agents
    compute it at call time and pass it through so it's consistent across
    backends.
    """

    text: str
    model: str
    prompt_hash: str


@runtime_checkable
class LLMClient(Protocol):
    """Call shape every Efterlev agent uses."""

    def complete(
        self,
        *,
        system: str,
        messages: list[LLMMessage],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Run a single completion. Returns (text, model, prompt_hash)."""
        ...


@dataclass
class StubLLMClient:
    """Test fixture: returns a preset response and records the last call.

    Agents tests inject an instance instead of reaching to the network.
    Set `response_text` before calling; inspect `last_system` / `last_messages`
    after to assert on prompt shape (e.g. that evidence was XML-fenced).
    """

    response_text: str = "{}"
    model: str = "stub-model"
    last_system: str = ""
    last_messages: list[LLMMessage] = field(default_factory=list)
    last_prompt_hash: str = ""
    call_count: int = 0

    def complete(
        self,
        *,
        system: str,
        messages: list[LLMMessage],
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        import hashlib

        self.last_system = system
        self.last_messages = list(messages)
        self.call_count += 1
        joined = system + "\n".join(m.content for m in messages)
        prompt_hash = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        self.last_prompt_hash = prompt_hash
        return LLMResponse(text=self.response_text, model=self.model, prompt_hash=prompt_hash)
