"""Central configuration for Local RAG (FastAPI backend).

Loads settings from environment variables / a local ``.env`` file using Pydantic.
Embeddings and retrieval always run locally; answer generation is delegated to a
selectable provider (Groq, Gemini, OpenRouter, HF Inference, or the local HF LLM).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (two levels up from this file: app/core/config.py -> backend/).
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings, populated from the environment or ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Logging ---
    log_level: str = Field(default="INFO")

    # --- Local storage paths ---
    # DATA_DIR should point at a persistent volume in the cloud (e.g. Fly.io /data).
    data_dir: Path = Field(default=BACKEND_DIR / "data")

    # --- CORS ---
    # Comma-separated list of allowed frontend origins. "*" allows any origin.
    cors_origins: str = Field(default="*")

    # --- RAG / embedding settings (local embeddings, no API key required) ---
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    embedding_dims: int = Field(default=384)
    lance_table_name: str = Field(default="documents")
    active_kb: str = Field(default="documents")
    top_k: int = Field(default=4)
    split_length: int = Field(default=250)
    split_overlap: int = Field(default=30)

    # --- Generation provider selection ---
    # One of: groq | gemini | openrouter | hf | local
    llm_provider: str = Field(default="groq")

    # Provider API keys (only the selected provider's key is required).
    groq_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")
    hf_token: str = Field(default="")

    # Optional per-provider default model overrides (blank = provider default).
    groq_model: str = Field(default="")
    gemini_model: str = Field(default="")
    openrouter_model: str = Field(default="")
    hf_model: str = Field(default="")

    # --- Generation knobs (shared across providers) ---
    llm_max_new_tokens: int = Field(default=512)
    llm_temperature: float = Field(default=0.3)
    llm_context_char_budget: int = Field(default=6000)

    # --- Local HF LLM (used only when llm_provider == "local") ---
    llm_model: str = Field(default="Qwen/Qwen2.5-0.5B-Instruct")

    # --- Derived paths ---
    @property
    def vector_store_dir(self) -> Path:
        return self.data_dir / "vector_store"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def lance_db_path(self) -> str:
        return str(self.vector_store_dir / "lancedb")

    @property
    def sqlite_path(self) -> str:
        return str(self.data_dir / "localrag.db")

    def ensure_dirs(self) -> None:
        """Create the local storage directories if they do not exist."""
        self.vector_store_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins or ["*"]


# Module-level singleton; import as ``from app.core.config import settings``.
settings = Settings()
