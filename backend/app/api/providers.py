"""Providers + settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.llm import registry

router = APIRouter(prefix="/api", tags=["providers"])


@router.get("/providers")
def get_providers() -> dict:
    return {
        "default_provider": settings.llm_provider,
        "providers": registry.list_providers(),
    }


class SettingsOut(BaseModel):
    top_k: int
    default_provider: str
    llm_max_new_tokens: int
    llm_temperature: float


@router.get("/settings", response_model=SettingsOut)
def get_settings() -> SettingsOut:
    return SettingsOut(
        top_k=settings.top_k,
        default_provider=settings.llm_provider,
        llm_max_new_tokens=settings.llm_max_new_tokens,
        llm_temperature=settings.llm_temperature,
    )
