"""Index arbitrary document corpora into isolated evaluation KBs.

BEIR-style corpora are ``{doc_id: text}`` maps rather than files, so this module
embeds and writes them directly (one Haystack ``Document`` per corpus doc, no
splitting) into a dedicated LanceDB table. The corpus ``doc_id`` is stored in the
existing ``file_path`` meta field, so retrieval maps 1:1 back to doc-ids without
any schema change — and the user's own knowledge bases are never touched.
"""

from __future__ import annotations

from haystack import Document
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy

from app.core.config import settings
from app.core.rag_pipeline import (
    _open_lance_table,
    clear_table,
    get_document_store,
    retrieve_with_sources,
)


def corpus_indexed(table_name: str) -> int:
    """Return how many docs are already indexed in ``table_name`` (0 if none)."""
    tbl = _open_lance_table(table_name)
    if tbl is None:
        return 0
    try:
        return tbl.count_rows()
    except Exception:  # pragma: no cover - defensive
        return len(tbl.to_pandas())


def index_corpus(
    corpus: dict[str, str],
    table_name: str,
    *,
    reuse: bool = False,
    batch_size: int = 256,
) -> int:
    """Embed and write ``{doc_id: text}`` into the ``table_name`` eval KB.

    With ``reuse=True`` an already-populated table is left as-is (skip re-embed).
    Otherwise the table is cleared first so counts stay exact. Returns the number
    of documents written (or already present when reused).
    """
    existing = corpus_indexed(table_name)
    if reuse and existing:
        return existing
    if existing:
        clear_table(table_name)

    store = get_document_store(table_name)
    embedder = SentenceTransformersDocumentEmbedder(model=settings.embedding_model)
    embedder.warm_up()
    writer = DocumentWriter(document_store=store, policy=DuplicatePolicy.OVERWRITE)

    doc_items = list(corpus.items())
    written = 0
    for start in range(0, len(doc_items), batch_size):
        batch = doc_items[start:start + batch_size]
        docs = [
            Document(content=text, meta={"file_path": doc_id, "file_type": "corpus"})
            for doc_id, text in batch
            if text and text.strip()
        ]
        if not docs:
            continue
        embedded = embedder.run(documents=docs)["documents"]
        written += writer.run(documents=embedded)["documents_written"]
    return written


def retrieve_doc_ids(query: str, table_name: str, top_k: int) -> list[str]:
    """Retrieve ``top_k`` doc-ids for ``query`` from an eval KB, best-rank first."""
    _, sources = retrieve_with_sources(query, top_k=top_k, table_name=table_name)
    return [s["file_path"] for s in sources]
