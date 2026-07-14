"""Evaluation metrics for the RAG suite — transparent, dependency-light.

Two families:

* **Retrieval / IR** metrics over ranked doc-ids vs. relevance judgements
  (``recall_at_k``, ``precision_at_k``, ``ndcg_at_k``, ``mrr``).
* **Generation** metrics that need no external judge: embedding-based
  ``semantic_similarity`` / ``answer_relevancy`` (reusing the app's local
  sentence-transformers model) and lexical ``faithfulness`` (n-gram overlap of
  the answer with its retrieved context).

Plus a tiny ``Timer`` context manager for latency measurements.
"""

from __future__ import annotations

import math
import re
import time
from contextlib import contextmanager
from typing import Iterable, Mapping, Sequence

import numpy as np

from app.core.config import settings

# --- Retrieval / IR metrics -----------------------------------------------------------

Relevance = Mapping[str, float]  # doc_id -> graded relevance (0 = irrelevant)


def _relevant_set(relevance: Relevance) -> set[str]:
    return {doc_id for doc_id, rel in relevance.items() if rel > 0}


def recall_at_k(ranked: Sequence[str], relevance: Relevance, k: int) -> float:
    """Fraction of relevant docs retrieved within the top-``k``."""
    rel = _relevant_set(relevance)
    if not rel:
        return 0.0
    hits = sum(1 for doc_id in ranked[:k] if doc_id in rel)
    return hits / len(rel)


def precision_at_k(ranked: Sequence[str], relevance: Relevance, k: int) -> float:
    """Fraction of the top-``k`` results that are relevant."""
    if k <= 0:
        return 0.0
    rel = _relevant_set(relevance)
    hits = sum(1 for doc_id in ranked[:k] if doc_id in rel)
    return hits / k


def _dcg(gains: Iterable[float]) -> float:
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(ranked: Sequence[str], relevance: Relevance, k: int) -> float:
    """Normalized DCG@k using graded relevance (0 when no judgements)."""
    if not relevance:
        return 0.0
    gains = [float(relevance.get(doc_id, 0.0)) for doc_id in ranked[:k]]
    dcg = _dcg(gains)
    ideal_gains = sorted((float(v) for v in relevance.values()), reverse=True)[:k]
    idcg = _dcg(ideal_gains)
    return dcg / idcg if idcg > 0 else 0.0


def mrr(ranked: Sequence[str], relevance: Relevance) -> float:
    """Reciprocal rank of the first relevant document (0 if none retrieved)."""
    rel = _relevant_set(relevance)
    for i, doc_id in enumerate(ranked, start=1):
        if doc_id in rel:
            return 1.0 / i
    return 0.0


# --- Text / embedding metrics (local, no external judge) ------------------------------

_embedder = None


def _get_embedder():
    """Lazily load the shared local embedding model (same as the app)."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def _embed(texts: Sequence[str]) -> np.ndarray:
    vecs = _get_embedder().encode(
        list(texts), convert_to_numpy=True, normalize_embeddings=True
    )
    return np.asarray(vecs, dtype=np.float32)


def semantic_similarity(a: str, b: str) -> float:
    """Cosine similarity of two texts in the local embedding space (0..1-ish)."""
    if not (a and a.strip()) or not (b and b.strip()):
        return 0.0
    va, vb = _embed([a, b])
    return float(np.dot(va, vb))  # already normalized -> cosine


def answer_relevancy(answer: str, question: str) -> float:
    """Proxy for how on-topic an answer is: cosine(answer, question)."""
    return semantic_similarity(answer, question)


_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+")

# Very common words are ignored so faithfulness reflects content overlap, not
# filler. Small, language-agnostic-ish stop list (English + Spanish basics).
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was", "were",
    "for", "on", "with", "as", "by", "that", "this", "it", "be", "at", "from",
    "el", "la", "los", "las", "un", "una", "de", "del", "y", "o", "en", "es",
    "son", "para", "con", "que", "por", "se", "su", "al", "lo",
}


def _content_tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOPWORDS]


def lexical_faithfulness(answer: str, context: str) -> float:
    """Share of the answer's content tokens (unigrams+bigrams) present in context.

    A grounding/hallucination proxy: 1.0 means every content token the model
    produced also appears in the retrieved context; low values flag ungrounded
    (potentially hallucinated) answers. Requires no LLM judge.
    """
    ans_tokens = _content_tokens(answer)
    if not ans_tokens:
        return 0.0
    ctx_tokens = _content_tokens(context)
    ctx_uni = set(ctx_tokens)
    ctx_bi = {f"{a} {b}" for a, b in zip(ctx_tokens, ctx_tokens[1:])}

    ans_uni = set(ans_tokens)
    ans_bi = {f"{a} {b}" for a, b in zip(ans_tokens, ans_tokens[1:])}
    grams = ans_uni | ans_bi
    if not grams:
        return 0.0
    covered = sum(1 for g in grams if (" " in g and g in ctx_bi) or (" " not in g and g in ctx_uni))
    return covered / len(grams)


def context_recall(retrieved_sources: Iterable[str], relevant_sources: Iterable[str]) -> float:
    """Fraction of the gold relevant sources that appear in the retrieved set."""
    rel = {s for s in relevant_sources if s}
    if not rel:
        return 0.0
    got = set(retrieved_sources)
    return len(rel & got) / len(rel)


def context_precision(retrieved_sources: Sequence[str], relevant_sources: Iterable[str]) -> float:
    """Fraction of the retrieved sources that are gold-relevant."""
    if not retrieved_sources:
        return 0.0
    rel = {s for s in relevant_sources if s}
    hits = sum(1 for s in retrieved_sources if s in rel)
    return hits / len(retrieved_sources)


# --- Latency --------------------------------------------------------------------------

class Timer:
    """Context manager measuring wall-clock seconds: ``with Timer() as t: ...``."""

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        self.seconds = 0.0
        return self

    def __exit__(self, *exc) -> None:
        self.seconds = time.perf_counter() - self._start


@contextmanager
def timed():
    """Yield a one-attribute object whose ``.seconds`` is set on exit."""
    t = Timer()
    with t:
        yield t


def mean(values: Iterable[float]) -> float:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else 0.0
