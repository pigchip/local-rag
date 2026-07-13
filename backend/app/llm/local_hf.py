"""Local, free text generation using HuggingFace ``transformers`` on CPU.

Ported from the original ``local_llm.py``. The model is loaded lazily as a
process-wide singleton so the (slow) first load happens once. Used only when
``LLM_PROVIDER=local``.
"""

from __future__ import annotations

import threading
from typing import Iterator

from app.core.config import settings
from app.core.logging_setup import get_logger
from app.llm.base import Generator, build_messages

log = get_logger("llm")

_lock = threading.Lock()
_pipe = None  # transformers pipeline
_tokenizer = None


def _load():
    """Lazily load the tokenizer + text-generation pipeline (once)."""
    global _pipe, _tokenizer
    if _pipe is not None:
        return
    with _lock:
        if _pipe is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

        model_id = settings.llm_model
        log.info("Loading local LLM '%s' (this can take a while on first run)…", model_id)
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
        _tokenizer = tokenizer
        _pipe = pipeline("text-generation", model=model, tokenizer=tokenizer)
        log.info("Local LLM ready.")


class LocalHFGenerator(Generator):
    name = "local"
    label = "Local (HuggingFace)"

    @property
    def available(self) -> bool:
        # Always "available" — the model downloads on first use. Requires torch.
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except Exception:
            return False
        return True

    def list_models(self) -> list[str]:
        return [settings.llm_model]

    def default_model(self) -> str:
        return settings.llm_model

    def generate(self, query: str, context: str, model: str | None = None) -> str:
        _load()
        messages = build_messages(query, context)
        temp = settings.llm_temperature
        kwargs: dict = {"max_new_tokens": settings.llm_max_new_tokens, "return_full_text": False}
        if temp and temp > 0:
            kwargs.update({"do_sample": True, "temperature": temp})
        else:
            kwargs["do_sample"] = False
        result = _pipe(messages, **kwargs)
        text = result[0]["generated_text"]
        if isinstance(text, list):
            text = text[-1].get("content", "") if text else ""
        return (text or "").strip()

    def stream(self, query: str, context: str, model: str | None = None) -> Iterator[str]:
        _load()
        from threading import Thread
        from transformers import TextIteratorStreamer

        messages = build_messages(query, context)
        prompt = _tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = _tokenizer(prompt, return_tensors="pt")
        streamer = TextIteratorStreamer(_tokenizer, skip_prompt=True, skip_special_tokens=True)

        gen_kwargs = {**inputs, "streamer": streamer, "max_new_tokens": settings.llm_max_new_tokens}
        temp = settings.llm_temperature
        if temp and temp > 0:
            gen_kwargs.update({"do_sample": True, "temperature": temp})
        else:
            gen_kwargs["do_sample"] = False

        log.info("Streaming answer via local LLM (%d chars of context)…", len(context))
        thread = Thread(target=_pipe.model.generate, kwargs=gen_kwargs, daemon=True)
        thread.start()
        for token in streamer:
            if token:
                yield token
        thread.join()
