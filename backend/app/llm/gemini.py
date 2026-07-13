"""Google Gemini generator (free-tier friendly).

Uses the Generative Language REST API's ``streamGenerateContent`` endpoint with
Server-Sent Events so tokens arrive incrementally.
"""

from __future__ import annotations

import json
from typing import Iterator

import httpx

from app.core.config import settings
from app.core.logging_setup import get_logger
from app.llm.base import Generator, build_messages

log = get_logger("llm")

_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiGenerator(Generator):
    name = "gemini"
    label = "Google Gemini"

    def __init__(self) -> None:
        self._models = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
        ]

    @property
    def api_key(self) -> str:
        return settings.gemini_api_key

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list[str]:
        return list(self._models)

    def default_model(self) -> str:
        return settings.gemini_model or self._models[0]

    def _body(self, query: str, context: str) -> dict:
        messages = build_messages(query, context)
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        body: dict = {
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": settings.llm_max_new_tokens,
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        temp = settings.llm_temperature
        if temp and temp > 0:
            body["generationConfig"]["temperature"] = temp
        return body

    def stream(self, query: str, context: str, model: str | None = None) -> Iterator[str]:
        if not self.available:
            raise RuntimeError("Provider 'gemini' is not configured (missing GEMINI_API_KEY).")
        model_id = model or self.default_model()
        url = f"{_BASE}/models/{model_id}:streamGenerateContent"
        params = {"alt": "sse", "key": self.api_key}
        log.info("Streaming answer via gemini (%s)…", model_id)
        with httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            with client.stream(
                "POST", url, params=params, json=self._body(query, context)
            ) as resp:
                if resp.status_code >= 400:
                    body = resp.read().decode("utf-8", "replace")
                    raise RuntimeError(f"gemini API error {resp.status_code}: {body[:500]}")
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if not data:
                        continue
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    for cand in chunk.get("candidates", []):
                        for part in (cand.get("content") or {}).get("parts", []):
                            text = part.get("text")
                            if text:
                                yield text
