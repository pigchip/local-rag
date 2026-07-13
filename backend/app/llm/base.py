"""Generator interface and shared prompt building for Local RAG.

A ``Generator`` turns a user query plus retrieved context into a grounded answer,
either all at once (``generate``) or token-by-token (``stream``). Concrete
implementations live alongside this module (Groq, Gemini, OpenRouter, HF
Inference, local HF) and are selected at runtime by :mod:`app.llm.registry`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from app.core.config import settings

SYSTEM_PROMPT = (
    "You are Local RAG, a helpful assistant that answers questions about a "
    "codebase and documents. Answer using ONLY the provided context. The context "
    "is a numbered list of sources, each starting with a marker like '[1] Source: "
    "<file>'. When you use information from a source, cite it inline with its "
    "number in square brackets, e.g. [1] or [2]. If the context does not contain "
    "the answer, say you don't have enough information in the knowledge base. Be "
    "concise."
)


def build_messages(query: str, context: str) -> list[dict]:
    """Assemble the chat messages, injecting the (budgeted) retrieved context."""
    budget = settings.llm_context_char_budget
    trimmed = context[:budget]
    if len(context) > budget:
        trimmed += "\n…[context truncated]…"
    user = (
        f"Context from the knowledge base:\n\n{trimmed}\n\n"
        f"---\n\nQuestion: {query}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


class Generator(ABC):
    """Base class for a pluggable answer generator."""

    #: Stable provider id used in the API and config (e.g. "groq").
    name: str = "base"
    #: Human-readable label shown in the UI.
    label: str = "Base"

    @property
    @abstractmethod
    def available(self) -> bool:
        """True when this provider is configured (e.g. its API key is set)."""

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return the selectable model ids for this provider."""

    @abstractmethod
    def default_model(self) -> str:
        """Return the default model id for this provider."""

    @abstractmethod
    def stream(self, query: str, context: str, model: str | None = None) -> Iterator[str]:
        """Yield answer tokens as they are generated, grounded in ``context``."""

    def generate(self, query: str, context: str, model: str | None = None) -> str:
        """Generate a complete answer (default: concatenate the stream)."""
        return "".join(self.stream(query, context, model=model)).strip()
