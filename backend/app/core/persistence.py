"""Optional cloud persistence for the data directory via a Hugging Face Dataset.

Hugging Face Spaces on the free tier have an *ephemeral* filesystem: anything the
app writes (SQLite DB + LanceDB vector store) survives restarts/sleep but is wiped
whenever the Space is rebuilt. To make knowledge bases and chat history durable we
mirror ``settings.data_dir`` to a (private) HF Dataset repo:

* :func:`restore` runs once at startup and pulls the latest snapshot down.
* :func:`mark_dirty` is called after any write; a background thread debounces those
  signals and uploads the changed data back to the dataset.

Everything here is a no-op unless both ``HF_DATASET_REPO`` and a write-capable HF
token (``HF_TOKEN`` / ``HUGGING_FACE_HUB_TOKEN``) are present, so local development
and other deployment targets are completely unaffected.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time

from app.core.config import settings
from app.core.logging_setup import get_logger

log = get_logger("persistence")

# Model cache is large and reproducible; never sync it to the dataset.
_IGNORE_PATTERNS = ["hf_cache/*", "hf_cache/**", "**/hf_cache/**", "*.lock"]

_DEBOUNCE_SECONDS = 20.0

_dirty = threading.Event()
_worker_started = False
_lock = threading.Lock()


def _repo_id() -> str:
    return os.environ.get("HF_DATASET_REPO", "").strip()


def _token() -> str:
    for var in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN"):
        val = os.environ.get(var, "")
        if val:
            return val
    return ""


def is_enabled() -> bool:
    return bool(_repo_id()) and bool(_token())


def restore() -> None:
    """Download the latest data snapshot from the HF Dataset into ``data_dir``."""
    if not is_enabled():
        return
    try:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import RepositoryNotFoundError

        settings.data_dir.mkdir(parents=True, exist_ok=True)
        try:
            snapshot_download(
                repo_id=_repo_id(),
                repo_type="dataset",
                local_dir=str(settings.data_dir),
                token=_token(),
            )
            log.info("Restored data from HF dataset %s", _repo_id())
        except RepositoryNotFoundError:
            _ensure_dataset_repo()
            log.info("HF dataset %s is new/empty; starting fresh", _repo_id())
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Data restore skipped (%s): %s", type(exc).__name__, exc)


def _ensure_dataset_repo() -> None:
    from huggingface_hub import HfApi

    HfApi(token=_token()).create_repo(
        repo_id=_repo_id(), repo_type="dataset", private=True, exist_ok=True
    )


def _checkpoint_sqlite() -> None:
    """Fold the WAL into the main DB file so the uploaded snapshot is consistent."""
    try:
        con = sqlite3.connect(settings.sqlite_path)
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        con.close()
    except Exception:  # pragma: no cover - best effort
        pass


def _upload() -> None:
    from huggingface_hub import HfApi

    _checkpoint_sqlite()
    HfApi(token=_token()).upload_folder(
        folder_path=str(settings.data_dir),
        repo_id=_repo_id(),
        repo_type="dataset",
        ignore_patterns=_IGNORE_PATTERNS,
        commit_message="Sync knowledge bases + sessions",
    )
    log.info("Backed up data to HF dataset %s", _repo_id())


def mark_dirty() -> None:
    """Signal that the data directory changed and should be backed up soon."""
    if is_enabled():
        _dirty.set()


def _worker() -> None:
    while True:
        _dirty.wait()
        # Debounce: wait for writes to settle before uploading.
        time.sleep(_DEBOUNCE_SECONDS)
        _dirty.clear()
        try:
            _upload()
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Data backup failed (%s): %s", type(exc).__name__, exc)


def start_background_sync() -> None:
    """Launch the debounced backup worker (idempotent)."""
    global _worker_started
    if not is_enabled():
        return
    with _lock:
        if _worker_started:
            return
        try:
            _ensure_dataset_repo()
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Could not ensure HF dataset repo: %s", exc)
        threading.Thread(target=_worker, name="hf-data-sync", daemon=True).start()
        _worker_started = True
        log.info("HF data-sync worker started (repo=%s)", _repo_id())
