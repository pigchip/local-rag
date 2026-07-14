"""Dataset loaders for the evaluation suite.

* ``load_golden_set()`` — the shipped, generic Q&A set over ``eval/sample_data/``.
* ``load_beir()`` — small BEIR datasets (SciFact, NFCorpus) from the HuggingFace
  Hub, returning ``(corpus, queries, qrels)`` with optional subsampling for a
  fast debug loop. Requires the optional ``datasets`` package
  (``requirements-eval.txt``).
"""

from __future__ import annotations

import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
GOLDEN_PATH = EVAL_DIR / "datasets" / "golden_set.json"
BEIR_CACHE = EVAL_DIR / "datasets" / "beir_cache"

# Friendly name -> HuggingFace dataset repo. Each has a matching ``*-qrels`` repo.
BEIR_DATASETS = {
    "scifact": "BeIR/scifact",
    "nfcorpus": "BeIR/nfcorpus",
}


def load_golden_set(path: Path | str = GOLDEN_PATH) -> list[dict]:
    """Load the golden Q&A set: a list of ``{id, question, ground_truth,
    relevant_sources}`` items."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    items = data["items"] if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        raise ValueError(f"Golden set at {path} is empty or malformed.")
    return items


def load_beir(
    name: str,
    split: str = "test",
    num_queries: int | None = None,
    max_corpus: int | None = None,
) -> tuple[dict[str, str], dict[str, str], dict[str, dict[str, float]]]:
    """Load a BEIR dataset as ``(corpus, queries, qrels)``.

    * ``corpus``  : ``{doc_id: "title\\ntext"}``
    * ``queries`` : ``{query_id: text}`` (only queries that have judgements)
    * ``qrels``   : ``{query_id: {doc_id: relevance}}``

    ``num_queries`` limits the evaluated queries; ``max_corpus`` caps the indexed
    corpus size (relevant docs are always kept, remaining slots filled with other
    docs as distractors) — both keep CPU-only runs fast.
    """
    try:
        from datasets import load_dataset
    except ImportError as exc:  # pragma: no cover - dependency guidance
        raise ImportError(
            "BEIR evaluation needs the 'datasets' package. Install the eval extras:\n"
            "    pip install -r requirements-eval.txt"
        ) from exc

    if name not in BEIR_DATASETS:
        raise ValueError(f"Unknown BEIR dataset '{name}'. Known: {sorted(BEIR_DATASETS)}")
    repo = BEIR_DATASETS[name]
    BEIR_CACHE.mkdir(parents=True, exist_ok=True)
    cache = str(BEIR_CACHE)

    # Relevance judgements first — they drive which queries/docs we keep.
    qrels_raw = load_dataset(f"{repo}-qrels", cache_dir=cache)[split]
    qrels: dict[str, dict[str, float]] = {}
    for row in qrels_raw:
        qid = str(row["query-id"])
        did = str(row["corpus-id"])
        score = float(row["score"])
        if score <= 0:
            continue
        qrels.setdefault(qid, {})[did] = score

    query_ids = list(qrels.keys())
    if num_queries is not None:
        query_ids = query_ids[:num_queries]
    qrels = {qid: qrels[qid] for qid in query_ids}

    queries_raw = load_dataset(repo, "queries", cache_dir=cache)["queries"]
    wanted_q = set(query_ids)
    queries = {
        str(r["_id"]): r["text"]
        for r in queries_raw
        if str(r["_id"]) in wanted_q
    }

    relevant_docs = {did for rels in qrels.values() for did in rels}
    corpus_raw = load_dataset(repo, "corpus", cache_dir=cache)["corpus"]

    corpus: dict[str, str] = {}
    extra_budget = None
    if max_corpus is not None:
        extra_budget = max(0, max_corpus - len(relevant_docs))
    for r in corpus_raw:
        did = str(r["_id"])
        title = (r.get("title") or "").strip()
        text = (r.get("text") or "").strip()
        content = f"{title}\n{text}".strip()
        if did in relevant_docs:
            corpus[did] = content
        elif extra_budget is None:
            corpus[did] = content
        elif extra_budget > 0:
            corpus[did] = content
            extra_budget -= 1

    return corpus, queries, qrels
