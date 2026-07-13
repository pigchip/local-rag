"""Knowledge-base service: create/list KBs, index uploads, generate descriptions."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.logging_setup import get_logger
from app.core import rag_pipeline as rag
from app.db import repo
from app.llm import registry

log = get_logger("kb")

_NAME_RE = re.compile(r"[^a-z0-9_]+")
# Citation artifacts that leak from the RAG system prompt (e.g. "[1]", "[no source number]").
_CITATION_RE = re.compile(r"\s*\[(?:\d+|no source[^\]]*|source[^\]]*)\]", re.IGNORECASE)


def _clean_description(text: str) -> str:
    """Strip citation markers/quotes the LLM may add and return a single tidy line."""
    line = text.splitlines()[0] if text.splitlines() else text
    line = _CITATION_RE.sub("", line)
    line = line.strip().strip('"').strip()
    # Collapse any doubled spaces left by removed markers and tidy stray space-before-period.
    line = re.sub(r"\s{2,}", " ", line)
    line = re.sub(r"\s+([.!?,;:])", r"\1", line)
    return line.strip()[:200]


def sanitize_kb_name(name: str) -> str:
    """Normalize a user-provided KB name into a safe LanceDB table name."""
    slug = _NAME_RE.sub("_", (name or "").strip().lower()).strip("_")
    return slug or "knowledge_base"


def _save_uploads(files: list[UploadFile], kb_name: str) -> list[Path]:
    """Persist uploaded files under the KB's uploads folder. Returns saved paths."""
    dest_dir = settings.uploads_dir / kb_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for f in files:
        if not f.filename:
            continue
        dest = dest_dir / Path(f.filename).name
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append(dest)
    return saved


def index_uploads(files: list[UploadFile], kb_name: str) -> int:
    """Save and index uploaded files into ``kb_name``. Returns chunks written."""
    saved = _save_uploads(files, kb_name)
    total = 0
    for path in saved:
        total += rag.index_path(path, None, kb_name)
    return total


def _parse_meta_response(text: str, fallback_desc: str) -> tuple[str, list[str]]:
    """Extract (description, examples) from an LLM response, tolerating loose JSON."""
    description, examples = fallback_desc, []
    obj = None
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group(0))
            except (ValueError, TypeError):
                obj = None
    if isinstance(obj, dict):
        desc = obj.get("description")
        if isinstance(desc, str) and desc.strip():
            description = _clean_description(desc)
        ex = obj.get("examples")
        if isinstance(ex, list):
            examples = [_clean_description(str(e)) for e in ex if str(e).strip()][:4]
    else:
        # Fallback: first line is the description, remaining non-empty lines are examples.
        lines = [ln.strip("-*0123456789. \t") for ln in text.splitlines() if ln.strip()]
        if lines:
            description = _clean_description(lines[0])
            examples = [_clean_description(l) for l in lines[1:5]]
    return description, examples


def describe_kb(
    kb_name: str, provider: str | None = None, model: str | None = None
) -> dict:
    """Generate + persist a description and example prompts for ``kb_name``.

    Uses the active LLM provider over document previews; falls back to a preview
    snippet (and no examples) if generation is unavailable or fails.
    """
    previews = rag.sample_previews(kb_name, limit=5)
    if not previews:
        repo.set_kb_description(kb_name, "Empty knowledge base.", examples=[])
        return {"description": "Empty knowledge base.", "examples": []}

    joined = "\n\n".join(previews)[: settings.llm_context_char_budget]
    description = previews[0][:180].strip()
    examples: list[str] = []
    try:
        gen = registry.get_generator(provider)
        if gen.available:
            prompt = (
                "You are given excerpts from a knowledge base. Respond with ONLY a JSON "
                "object (no markdown, no prose) of the form:\n"
                '{"description": "<one concise sentence, max 25 words, describing what '
                'this knowledge base is about>", "examples": ["<question>", "<question>", '
                '"<question>"]}\n'
                "The 3 examples must be natural, specific questions a user could ask that "
                "this knowledge base can answer. Do not include citations or source markers.\n\n"
                f"Excerpts:\n{joined}"
            )
            raw = gen.generate(prompt, context="", model=model).strip()
            if raw:
                description, examples = _parse_meta_response(raw, description)
    except Exception as exc:  # never block KB creation on description failure
        log.warning("Describe for KB '%s' fell back to preview: %s", kb_name, exc)

    repo.set_kb_description(kb_name, description, examples=examples)
    return {"description": description, "examples": examples}


def generate_description(kb_name: str, provider: str | None = None, model: str | None = None) -> str:
    """Backwards-compatible wrapper returning just the description."""
    return describe_kb(kb_name, provider, model)["description"]


def create_kb(
    name: str,
    files: list[UploadFile],
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    """Create a new KB from uploaded files, index them, and describe it."""
    kb_name = sanitize_kb_name(name)
    written = index_uploads(files, kb_name)
    meta = describe_kb(kb_name, provider, model)
    file_count, chunk_count = rag.kb_stats(kb_name)
    log.info("Created KB '%s' (%d files, %d chunks)", kb_name, file_count, chunk_count)
    return {
        "name": kb_name,
        "description": meta["description"],
        "examples": meta["examples"],
        "file_count": file_count,
        "chunk_count": chunk_count,
        "chunks_written": written,
    }


def add_files(
    kb_name: str,
    files: list[UploadFile],
    regenerate_description: bool = True,
    provider: str | None = None,
    model: str | None = None,
) -> dict:
    """Add individual/batch files to an existing KB."""
    written = index_uploads(files, kb_name)
    if regenerate_description:
        describe_kb(kb_name, provider, model)
    file_count, chunk_count = rag.kb_stats(kb_name)
    return {
        "name": kb_name,
        "description": repo.get_kb_description(kb_name),
        "examples": repo.get_kb_examples(kb_name),
        "file_count": file_count,
        "chunk_count": chunk_count,
        "chunks_written": written,
    }


def list_kbs() -> list[dict]:
    """Return every KB with its description, example prompts, and stats."""
    meta = repo.all_kb_meta()
    out = []
    for name in rag.list_tables():
        file_count, chunk_count = rag.kb_stats(name)
        m = meta.get(name, {})
        out.append({
            "name": name,
            "description": m.get("description", ""),
            "examples": m.get("examples", []),
            "file_count": file_count,
            "chunk_count": chunk_count,
        })
    return out


def list_files(kb_name: str) -> list[dict]:
    return rag.list_indexed_files(kb_name)


def delete_file(kb_name: str, file_path: str) -> int:
    return rag.delete_file(file_path, kb_name)


def clear_kb(kb_name: str) -> None:
    rag.clear_table(kb_name)
    repo.delete_kb_description(kb_name)
    upload_dir = settings.uploads_dir / kb_name
    if upload_dir.exists():
        shutil.rmtree(upload_dir, ignore_errors=True)
