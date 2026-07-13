"""Headless RAG pipelines for Local RAG (retrieval only — no text generation).

Two Haystack 2.x pipelines over a persistent LanceDB store:

* ``build_indexing_pipeline()`` — parse, split, embed, and write documents.
* ``build_query_pipeline()`` / ``retrieve_with_sources()`` — embed a query and
  fetch the most relevant chunks.

Embeddings are produced locally with sentence-transformers, so no API key is
required for retrieval. Answer generation lives in ``app.llm`` and is provider
selectable (Groq, Gemini, OpenRouter, HF Inference, or local HF).
"""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
from haystack import Pipeline
from haystack.dataclasses import ByteStream
from haystack.components.converters import (
    MarkdownToDocument,
    PyPDFToDocument,
    TextFileToDocument,
)
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.joiners import DocumentJoiner
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.routers import FileTypeRouter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from lancedb_haystack import LanceDBDocumentStore

from app.core.config import settings
from app.core.logging_setup import INDEX, QUERY, get_logger

log = get_logger("rag")

# Process-wide "active" knowledge base default (per-request table names override it).
_active_table: str | None = None


def set_active_table(table_name: str) -> None:
    """Select the knowledge-base table that retrieval/indexing default to."""
    global _active_table
    _active_table = table_name
    log.info("%s Active knowledge base set to '%s'", QUERY, table_name)


def get_active_table() -> str:
    """Return the currently active KB table name."""
    return _active_table or settings.active_kb or settings.lance_table_name


def list_tables() -> list[str]:
    """Return the names of all knowledge-base tables in the local LanceDB store."""
    import lancedb

    db_path = settings.lance_db_path
    if not Path(db_path).exists():
        return []
    try:
        db = lancedb.connect(db_path)
        return sorted(db.table_names())
    except Exception:  # pragma: no cover - defensive: never block the UI
        return []


# MIME types we route to dedicated converters.
PDF_MIME = "application/pdf"
MD_MIME = "text/markdown"
TXT_MIME = "text/plain"

CODE_SUFFIXES = (
    ".py", ".js", ".ts", ".txt", ".json", ".toml", ".yaml", ".yml",
    ".cfg", ".ini", ".sh", ".go", ".rs", ".java", ".c", ".cpp", ".h",
)
MD_SUFFIXES = (".md", ".markdown")

INDEXABLE_SUFFIXES = {".pdf", *MD_SUFFIXES, *CODE_SUFFIXES}

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "workspace_data", ".chainlit"}


def _metadata_schema() -> pa.StructType:
    """Minimal metadata schema; keys outside this set are dropped by LanceDB."""
    return pa.struct([("file_path", pa.string()), ("file_type", pa.string())])


def get_document_store(table_name: str | None = None) -> LanceDBDocumentStore:
    """Return a persistent LanceDB document store for ``table_name``."""
    settings.ensure_dirs()
    table = table_name or get_active_table()
    return LanceDBDocumentStore(
        database=settings.lance_db_path,
        table_name=table,
        metadata_schema=_metadata_schema(),
        embedding_dims=settings.embedding_dims,
    )


def build_indexing_pipeline(document_store: LanceDBDocumentStore | None = None) -> Pipeline:
    """Assemble the parse -> split -> embed -> write indexing pipeline."""
    store = document_store or get_document_store()

    router = FileTypeRouter(mime_types=[PDF_MIME, MD_MIME, TXT_MIME])
    splitter = DocumentSplitter(
        split_by="word",
        split_length=settings.split_length,
        split_overlap=settings.split_overlap,
    )
    embedder = SentenceTransformersDocumentEmbedder(model=settings.embedding_model)
    writer = DocumentWriter(document_store=store, policy=DuplicatePolicy.OVERWRITE)

    pipe = Pipeline()
    pipe.add_component("router", router)
    pipe.add_component("pdf", PyPDFToDocument())
    pipe.add_component("markdown", MarkdownToDocument())
    pipe.add_component("text", TextFileToDocument())
    pipe.add_component("joiner", DocumentJoiner())
    pipe.add_component("splitter", splitter)
    pipe.add_component("embedder", embedder)
    pipe.add_component("writer", writer)

    pipe.connect(f"router.{PDF_MIME}", "pdf.sources")
    pipe.connect(f"router.{MD_MIME}", "markdown.sources")
    pipe.connect(f"router.{TXT_MIME}", "text.sources")
    pipe.connect("pdf.documents", "joiner.documents")
    pipe.connect("markdown.documents", "joiner.documents")
    pipe.connect("text.documents", "joiner.documents")
    pipe.connect("joiner.documents", "splitter.documents")
    pipe.connect("splitter.documents", "embedder.documents")
    pipe.connect("embedder.documents", "writer.documents")
    return pipe


def collect_files(path: str | Path) -> list[Path]:
    """Recursively gather indexable files under ``path`` (skipping noise dirs)."""
    root = Path(path)
    if root.is_file():
        return [root] if root.suffix.lower() in INDEXABLE_SUFFIXES else []
    files: list[Path] = []
    for p in root.rglob("*"):
        if p.is_dir():
            continue
        rel_parts = p.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if p.suffix.lower() in INDEXABLE_SUFFIXES:
            files.append(p)
    return files


def _classify_mime(path: Path) -> str:
    """Map a file extension to one of our router MIME types (no global state)."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PDF_MIME
    if suffix in MD_SUFFIXES:
        return MD_MIME
    return TXT_MIME


def _to_source(path: Path) -> ByteStream:
    """Read a file into a ByteStream tagged with an explicit MIME type and path."""
    stream = ByteStream(data=path.read_bytes(), mime_type=_classify_mime(path))
    stream.meta["file_path"] = str(path)
    return stream


def index_path(
    path: str | Path,
    document_store: LanceDBDocumentStore | None = None,
    table_name: str | None = None,
) -> int:
    """Index every supported file under ``path``. Returns the chunk count written."""
    table = table_name or get_active_table()
    files = collect_files(path)
    log.info("%s Indexing '%s' into KB '%s' — %d file(s) found", INDEX, path, table, len(files))
    if not files:
        log.warning("%s No indexable files found under %s", INDEX, path)
        return 0

    store = document_store or get_document_store(table)
    pipe = build_indexing_pipeline(store)
    sources = [_to_source(f) for f in files]
    log.debug("%s Files: %s", INDEX, ", ".join(f.name for f in files))
    result = pipe.run({"router": {"sources": sources}})
    written = result.get("writer", {}).get("documents_written", 0)
    log.info("%s Indexed %d chunk(s) from %d file(s) into KB '%s'", INDEX, written, len(files), table)
    return written


# ---------------------------------------------------------------------------
# Query / retrieval pipeline — retrieval only, no text generation.
# ---------------------------------------------------------------------------

_query_pipelines: dict[str, Pipeline] = {}


def build_query_pipeline(document_store: LanceDBDocumentStore | None = None) -> Pipeline:
    """Assemble the embed-query -> retrieve pipeline."""
    from lancedb_haystack import LanceDBEmbeddingRetriever
    from haystack.components.embedders import SentenceTransformersTextEmbedder

    store = document_store or get_document_store()
    pipe = Pipeline()
    pipe.add_component("embedder", SentenceTransformersTextEmbedder(model=settings.embedding_model))
    pipe.add_component("retriever", LanceDBEmbeddingRetriever(document_store=store))
    pipe.connect("embedder.embedding", "retriever.query_embedding")
    return pipe


def _get_query_pipeline(table_name: str | None = None) -> Pipeline:
    table = table_name or get_active_table()
    pipe = _query_pipelines.get(table)
    if pipe is None:
        log.debug("%s Building query pipeline for KB '%s'", QUERY, table)
        pipe = build_query_pipeline(get_document_store(table))
        pipe.warm_up()
        _query_pipelines[table] = pipe
    return pipe


def _format_documents(documents: list) -> str:
    """Render retrieved documents as a single numbered text payload."""
    if not documents:
        return "No relevant context was found in the indexed knowledge base."
    blocks = []
    for i, doc in enumerate(documents, start=1):
        source = Path((doc.meta or {}).get("file_path", "unknown")).name
        blocks.append(f"[{i}] Source: {source}\n{doc.content}")
    return "\n\n".join(blocks)


def retrieve_with_sources(
    query: str,
    top_k: int | None = None,
    table_name: str | None = None,
) -> tuple[str, list[dict]]:
    """Search the active (or given) KB and return ``(context, sources)``."""
    table = table_name or get_active_table()
    pipe = _get_query_pipeline(table)
    k = top_k or settings.top_k
    log.info("%s Query KB '%s' (top_k=%d): %r", QUERY, table, k, query)
    result = pipe.run({
        "embedder": {"text": query},
        "retriever": {"top_k": k},
    })
    documents = result.get("retriever", {}).get("documents", [])
    sources: list[dict] = []
    for i, doc in enumerate(documents, start=1):
        file_path = (doc.meta or {}).get("file_path", "unknown")
        score = getattr(doc, "score", None)
        sources.append({
            "index": i,
            "source": Path(file_path).name,
            "file_path": file_path,
            "score": score,
            "content": doc.content or "",
        })
    log.info("%s Retrieved %d chunk(s) from KB '%s'", QUERY, len(documents), table)
    return _format_documents(documents), sources


def retrieve(query: str, top_k: int | None = None, table_name: str | None = None) -> str:
    """Embed ``query`` locally, search the active (or given) KB, return formatted text."""
    context, _ = retrieve_with_sources(query, top_k=top_k, table_name=table_name)
    return context


# ---------------------------------------------------------------------------
# Knowledge-base management (list / delete files, clear a KB).
# ---------------------------------------------------------------------------


def _open_lance_table(table_name: str):
    """Open the underlying LanceDB table, or return ``None`` if it doesn't exist."""
    import lancedb

    db_path = settings.lance_db_path
    if not Path(db_path).exists():
        return None
    db = lancedb.connect(db_path)
    if table_name not in db.table_names():
        return None
    return db.open_table(table_name)


def list_indexed_files(table_name: str | None = None) -> list[dict]:
    """Return the files indexed in ``table_name`` with chunk counts and a preview."""
    table = table_name or get_active_table()
    tbl = _open_lance_table(table)
    if tbl is None:
        return []
    df = tbl.to_pandas()
    grouped: dict[str, dict] = {}
    for _, row in df.iterrows():
        meta = row.get("meta") or {}
        file_path = meta.get("file_path") or "unknown"
        entry = grouped.setdefault(file_path, {
            "file_path": file_path,
            "name": Path(file_path).name,
            "chunks": 0,
            "preview": "",
        })
        entry["chunks"] += 1
        if not entry["preview"]:
            entry["preview"] = (str(row.get("content") or "").strip())[:200]
    return sorted(grouped.values(), key=lambda e: e["name"].lower())


def kb_stats(table_name: str) -> tuple[int, int]:
    """Return ``(file_count, chunk_count)`` for ``table_name``."""
    files = list_indexed_files(table_name)
    return len(files), sum(f["chunks"] for f in files)


def sample_previews(table_name: str, limit: int = 5) -> list[str]:
    """Return up to ``limit`` chunk previews for building a KB description."""
    files = list_indexed_files(table_name)
    previews = [f["preview"] for f in files if f.get("preview")]
    return previews[:limit]


def delete_file(file_path: str, table_name: str | None = None) -> int:
    """Delete every chunk originating from ``file_path``. Returns the count removed."""
    table = table_name or get_active_table()
    tbl = _open_lance_table(table)
    if tbl is None:
        return 0
    df = tbl.to_pandas()
    ids = [
        row["id"]
        for _, row in df.iterrows()
        if (row.get("meta") or {}).get("file_path") == file_path
    ]
    if not ids:
        return 0
    id_list = ", ".join("'" + str(i).replace("'", "''") + "'" for i in ids)
    tbl.delete(f"id IN ({id_list})")
    _query_pipelines.pop(table, None)
    log.info("%s Deleted %d chunk(s) for %s from KB '%s'", INDEX, len(ids), file_path, table)
    return len(ids)


def clear_table(table_name: str | None = None) -> None:
    """Drop the whole KB table and evict its cached pipeline."""
    import lancedb

    table = table_name or get_active_table()
    db_path = settings.lance_db_path
    if Path(db_path).exists():
        db = lancedb.connect(db_path)
        if table in db.table_names():
            db.drop_table(table)
            log.info("%s Cleared knowledge base '%s'", INDEX, table)
    _query_pipelines.pop(table, None)
