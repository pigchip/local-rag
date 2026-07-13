"""Provider registry — selects and describes the available answer generators.

The active provider defaults to ``settings.llm_provider`` but every request can
override it (``provider`` / ``model`` fields), so the frontend can offer a live
provider + model picker.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.core.logging_setup import get_logger
from app.llm.base import Generator
from app.llm.gemini import GeminiGenerator
from app.llm.local_hf import LocalHFGenerator
from app.llm.openai_compat import (
    GroqGenerator,
    HFInferenceGenerator,
    OpenRouterGenerator,
)

log = get_logger("llm")


@lru_cache(maxsize=1)
def _generators() -> dict[str, Generator]:
    instances: list[Generator] = [
        GroqGenerator(),
        GeminiGenerator(),
        OpenRouterGenerator(),
        HFInferenceGenerator(),
        LocalHFGenerator(),
    ]
    return {g.name: g for g in instances}


def list_providers() -> list[dict]:
    """Return provider metadata for the UI (id, label, configured, models)."""
    out = []
    for name, gen in _generators().items():
        out.append({
            "id": name,
            "label": gen.label,
            "available": gen.available,
            "models": gen.list_models(),
            "default_model": gen.default_model(),
        })
    return out


def get_generator(provider: str | None = None) -> Generator:
    """Return the generator for ``provider`` (or the configured default)."""
    name = (provider or settings.llm_provider or "groq").strip().lower()
    gens = _generators()
    gen = gens.get(name)
    if gen is None:
        raise ValueError(f"Unknown LLM provider '{name}'. Available: {sorted(gens)}")
    return gen


def resolve(provider: str | None, model: str | None) -> tuple[Generator, str]:
    """Return ``(generator, model)`` for a request, applying provider defaults."""
    gen = get_generator(provider)
    return gen, (model or gen.default_model())
