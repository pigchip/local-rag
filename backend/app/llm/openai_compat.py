"""OpenAI-compatible chat-completions generators (Groq, OpenRouter, HF Inference).

Groq, OpenRouter and the Hugging Face Inference router all expose an
OpenAI-compatible ``/chat/completions`` endpoint with streaming, so they share a
single implementation that differs only in base URL, API key, and model list.
"""

from __future__ import annotations

import json
from typing import Iterator

import httpx

from app.core.config import settings
from app.core.logging_setup import get_logger
from app.llm.base import Generator, build_messages

log = get_logger("llm")


class OpenAICompatGenerator(Generator):
    """A generator backed by an OpenAI-compatible chat-completions API."""

    base_url: str = ""
    #: Extra headers merged into every request (e.g. OpenRouter attribution).
    extra_headers: dict[str, str] = {}

    def __init__(self, models: list[str], model_override: str = "") -> None:
        self._models = models
        self._model_override = model_override

    # -- configuration -----------------------------------------------------
    @property
    def api_key(self) -> str:  # pragma: no cover - overridden per provider
        return ""

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def list_models(self) -> list[str]:
        return list(self._models)

    def default_model(self) -> str:
        return self._model_override or (self._models[0] if self._models else "")

    # -- generation --------------------------------------------------------
    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        return headers

    def _payload(self, query: str, context: str, model: str | None, stream: bool) -> dict:
        payload: dict = {
            "model": model or self.default_model(),
            "messages": build_messages(query, context),
            "max_tokens": settings.llm_max_new_tokens,
            "stream": stream,
        }
        temp = settings.llm_temperature
        if temp and temp > 0:
            payload["temperature"] = temp
        return payload

    def stream(self, query: str, context: str, model: str | None = None) -> Iterator[str]:
        if not self.available:
            raise RuntimeError(
                f"Provider '{self.name}' is not configured (missing API key)."
            )
        url = f"{self.base_url}/chat/completions"
        payload = self._payload(query, context, model, stream=True)
        log.info("Streaming answer via %s (%s)…", self.name, payload["model"])
        with httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            with client.stream("POST", url, headers=self._headers(), json=payload) as resp:
                if resp.status_code >= 400:
                    body = resp.read().decode("utf-8", "replace")
                    raise RuntimeError(f"{self.name} API error {resp.status_code}: {body[:500]}")
                for line in resp.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    token = delta.get("content")
                    if token:
                        yield token


class GroqGenerator(OpenAICompatGenerator):
    name = "groq"
    label = "Groq"
    base_url = "https://api.groq.com/openai/v1"

    def __init__(self) -> None:
        super().__init__(
            models=[
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "qwen-2.5-32b",
                "gemma2-9b-it",
            ],
            model_override=settings.groq_model,
        )

    @property
    def api_key(self) -> str:
        return settings.groq_api_key


class OpenRouterGenerator(OpenAICompatGenerator):
    name = "openrouter"
    label = "OpenRouter"
    base_url = "https://openrouter.ai/api/v1"
    extra_headers = {
        "HTTP-Referer": "https://local-rag.app",
        "X-Title": "Local RAG",
    }

    def __init__(self) -> None:
        super().__init__(
            models=[
                "meta-llama/llama-3.3-70b-instruct:free",
                "deepseek/deepseek-chat-v3-0324:free",
                "qwen/qwen-2.5-72b-instruct:free",
                "google/gemma-3-27b-it:free",
            ],
            model_override=settings.openrouter_model,
        )

    @property
    def api_key(self) -> str:
        return settings.openrouter_api_key


class HFInferenceGenerator(OpenAICompatGenerator):
    name = "hf"
    label = "Hugging Face"
    base_url = "https://router.huggingface.co/v1"

    def __init__(self) -> None:
        super().__init__(
            models=[
                "meta-llama/Llama-3.1-8B-Instruct",
                "Qwen/Qwen2.5-7B-Instruct",
                "mistralai/Mistral-7B-Instruct-v0.3",
            ],
            model_override=settings.hf_model,
        )

    @property
    def api_key(self) -> str:
        return settings.hf_token
