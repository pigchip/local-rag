"""Session + message endpoints, including the SSE chat-streaming route."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db import repo
from app.services import chat_service

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    title: str | None = None
    kb_name: str | None = None
    provider: str | None = None
    model: str | None = None


class SessionUpdate(BaseModel):
    title: str | None = None
    kb_name: str | None = None
    provider: str | None = None
    model: str | None = None


class ChatRequest(BaseModel):
    query: str
    kb_name: str | None = None
    top_k: int | None = None
    provider: str | None = None
    model: str | None = None


@router.get("")
def list_sessions() -> dict:
    return {"sessions": repo.list_sessions()}


@router.post("")
def create_session(body: SessionCreate) -> dict:
    return repo.create_session(
        title=body.title or "New chat",
        kb_name=body.kb_name,
        provider=body.provider,
        model=body.model,
    )


@router.get("/{session_id}")
def get_session(session_id: str) -> dict:
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.patch("/{session_id}")
def update_session(session_id: str, body: SessionUpdate) -> dict:
    session = repo.update_session(session_id, **body.model_dump())
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.delete("/{session_id}")
def delete_session(session_id: str) -> dict:
    if not repo.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"deleted": session_id}


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/{session_id}/messages")
def send_message(session_id: str, body: ChatRequest) -> StreamingResponse:
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    query = (body.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    kb_name = body.kb_name or session.get("kb_name")
    if not kb_name:
        raise HTTPException(status_code=400, detail="No knowledge base selected.")

    provider = body.provider or session.get("provider")
    model = body.model or session.get("model")

    # Persist any newly chosen KB/provider/model onto the session.
    repo.update_session(session_id, kb_name=kb_name, provider=provider, model=model)

    def event_stream():
        try:
            for event in chat_service.stream_answer(
                session_id, query, kb_name,
                top_k=body.top_k, provider=provider, model=model,
            ):
                yield _sse(event)
        except Exception as exc:  # pragma: no cover - defensive
            yield _sse({"type": "error", "error": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
