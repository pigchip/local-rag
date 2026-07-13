"""FastAPI application entrypoint for Local RAG."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# An empty HF token (e.g. `HF_TOKEN=` in .env) makes huggingface_hub send an
# illegal `Authorization: Bearer ` header when downloading the embedding model.
# Drop empty HF token vars from the environment so anonymous downloads work.
# (Settings still read the real provider value from .env for the `hf` provider.)
for _var in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "HUGGINGFACE_TOKEN"):
    if os.environ.get(_var, None) == "":
        os.environ.pop(_var, None)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import kb, providers, sessions
from app.core.config import settings
from app.core.logging_setup import get_logger
from app.db.database import init_db

log = get_logger("app")

app = FastAPI(title="Local RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kb.router)
app.include_router(sessions.router)
app.include_router(providers.router)


@app.on_event("startup")
def _startup() -> None:
    settings.ensure_dirs()
    init_db()
    log.info("Local RAG API ready (provider=%s, data_dir=%s)", settings.llm_provider, settings.data_dir)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
