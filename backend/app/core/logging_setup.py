"""Shared logging configuration for Local RAG.

Provides a single ``get_logger`` helper and one-time root configuration so every
module logs to the terminal with a consistent, readable format. The verbosity is
controlled by the ``LOG_LEVEL`` environment variable (default ``INFO``).
"""

from __future__ import annotations

import logging
import os

_CONFIGURED = False

# Short ASCII tags make the RAG flow easy to scan and are safe on every terminal.
INDEX = "[INDEX]"
QUERY = "[QUERY]"
TOOL = "[TOOL]"
USAGE = "[USAGE]"
SESSION = "[SESSION]"


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once. Safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)-18s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    root = logging.getLogger("localrag")
    root.setLevel(getattr(logging, log_level, logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False

    # Quiet down noisy third-party loggers unless explicitly debugging.
    if log_level != "DEBUG":
        for noisy in ("sentence_transformers", "haystack", "httpx", "httpcore"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced child logger, configuring logging on first use."""
    configure_logging()
    return logging.getLogger(f"localrag.{name}")
