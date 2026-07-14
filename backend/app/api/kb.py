"""Knowledge-base endpoints: list, create, add files, list/delete files, clear."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core import persistence
from app.services import kb_service

router = APIRouter(prefix="/api/kb", tags=["knowledge-base"])


@router.get("")
def list_kbs() -> dict:
    return {"knowledge_bases": kb_service.list_kbs()}


@router.post("/{kb_name}/describe")
def describe_kb(
    kb_name: str,
    provider: str | None = Form(None),
    model: str | None = Form(None),
) -> dict:
    """(Re)generate the description and example prompts for an existing KB."""
    if kb_name not in kb_service.rag.list_tables():
        raise HTTPException(status_code=404, detail=f"Knowledge base '{kb_name}' not found.")
    result = kb_service.describe_kb(kb_name, provider=provider, model=model)
    persistence.mark_dirty()
    return result


@router.post("")
async def create_kb(
    name: str = Form(...),
    provider: str | None = Form(None),
    model: str | None = Form(None),
    files: list[UploadFile] = File(...),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")
    result = kb_service.create_kb(name, files, provider=provider, model=model)
    if result["chunk_count"] == 0:
        raise HTTPException(
            status_code=422,
            detail="No indexable content was found in the uploaded file(s).",
        )
    persistence.mark_dirty()
    return result


@router.get("/{kb_name}/files")
def list_files(kb_name: str) -> dict:
    return {"files": kb_service.list_files(kb_name)}


@router.post("/{kb_name}/files")
async def add_files(
    kb_name: str,
    provider: str | None = Form(None),
    model: str | None = Form(None),
    regenerate_description: bool = Form(True),
    files: list[UploadFile] = File(...),
) -> dict:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")
    result = kb_service.add_files(
        kb_name, files, regenerate_description=regenerate_description,
        provider=provider, model=model,
    )
    persistence.mark_dirty()
    return result


@router.delete("/{kb_name}/files")
def delete_file(kb_name: str, file_path: str) -> dict:
    removed = kb_service.delete_file(kb_name, file_path)
    if removed == 0:
        raise HTTPException(status_code=404, detail="File not found in knowledge base.")
    persistence.mark_dirty()
    return {"removed_chunks": removed}


@router.delete("/{kb_name}")
def clear_kb(kb_name: str) -> dict:
    kb_service.clear_kb(kb_name)
    persistence.mark_dirty()
    return {"cleared": kb_name}
