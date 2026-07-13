"""Chat orchestration: retrieve -> stream a grounded answer -> persist messages."""

from __future__ import annotations

from typing import Iterator

from app.core.config import settings
from app.core import rag_pipeline as rag
from app.core.logging_setup import get_logger
from app.db import repo
from app.llm import registry

log = get_logger("chat")


def stream_answer(
    session_id: str,
    query: str,
    kb_name: str,
    top_k: int | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> Iterator[dict]:
    """Yield streaming events for a chat turn.

    Events (dicts) are one of:
      * ``{"type": "sources", "sources": [...]}`` — retrieved citations (first).
      * ``{"type": "token", "text": "..."}``      — a generated token.
      * ``{"type": "done", "message": {...}}``    — persisted assistant message.
      * ``{"type": "error", "error": "..."}``     — generation failure.
    """
    # Persist the user's message immediately.
    repo.add_message(session_id, "user", query)

    k = top_k or settings.top_k
    context, sources = rag.retrieve_with_sources(query, top_k=k, table_name=kb_name)
    yield {"type": "sources", "sources": sources}

    gen, resolved_model = registry.resolve(provider, model)
    parts: list[str] = []
    try:
        for token in gen.stream(query, context, model=resolved_model):
            parts.append(token)
            yield {"type": "token", "text": token}
    except Exception as exc:  # surface generation failures cleanly
        err = f"Generation error: {exc}"
        log.error("%s (provider=%s)", err, gen.name)
        answer = "".join(parts) or ""
        message = repo.add_message(session_id, "assistant", answer, sources)
        yield {"type": "error", "error": err, "message": message}
        return

    answer = "".join(parts).strip() or "(no response)"
    message = repo.add_message(session_id, "assistant", answer, sources)
    yield {"type": "done", "message": message}
