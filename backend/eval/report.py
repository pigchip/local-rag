"""Shared reporting helpers: config snapshots + timestamped result files.

Every run captures the settings that affect quality (models, chunking, top_k) so
reports are comparable over time and you can see whether a change moved the
metrics.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from app.core.config import settings

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def config_snapshot() -> dict:
    """Return the quality-affecting settings for run-to-run comparison."""
    return {
        "embedding_model": settings.embedding_model,
        "llm_model": settings.llm_model,
        "top_k": settings.top_k,
        "split_length": settings.split_length,
        "split_overlap": settings.split_overlap,
        "llm_max_new_tokens": settings.llm_max_new_tokens,
        "llm_temperature": settings.llm_temperature,
    }


def save_report(kind: str, payload: dict, out: Path | str | None = None) -> Path:
    """Write ``payload`` (with a config snapshot + timestamp) to a JSON report."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    record = {
        "kind": kind,
        "timestamp": stamp,
        "config": config_snapshot(),
        **payload,
    }
    path = Path(out) if out else RESULTS_DIR / f"{kind}-{stamp}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def fmt_pct(x: float) -> str:
    return f"{100 * x:5.1f}%"


def fmt_num(x: float) -> str:
    return f"{x:6.3f}"
