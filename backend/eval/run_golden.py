"""End-to-end evaluation over the shipped golden set.

Indexes ``eval/sample_data/`` into an isolated ``eval_golden`` KB, then for each
golden question retrieves context, generates an answer with the configured
provider, and reports judge-free generation metrics plus retrieval-context and
latency metrics.

Run from the ``backend/`` directory::

    .venv/Scripts/python.exe -m eval.run_golden                    # full set
    .venv/Scripts/python.exe -m eval.run_golden --limit 3          # fast smoke
    .venv/Scripts/python.exe -m eval.run_golden --provider local   # offline LLM
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import settings
from app.core.rag_pipeline import index_path, retrieve_with_sources
from app.llm import registry

from eval import metrics
from eval.data import load_golden_set
from eval.report import fmt_num, fmt_pct, save_report

SAMPLE_DIR = Path(__file__).resolve().parent / "sample_data"
GOLDEN_KB = "eval_golden"


def _unique_sources(sources: list[dict]) -> list[str]:
    seen: list[str] = []
    for s in sources:
        if s["source"] not in seen:
            seen.append(s["source"])
    return seen


def run(top_k: int, limit: int | None, out: str | None, provider: str | None = None) -> dict:
    settings.ensure_dirs()
    items = load_golden_set()
    if limit:
        items = items[:limit]

    gen, model = registry.resolve(provider, None)
    if not gen.available:
        raise SystemExit(
            f"Provider '{gen.name}' is not available (missing API key?). "
            f"Set the key in backend/.env or pass --provider <one-with-a-key>."
        )
    print(f"Using provider '{gen.name}' (model={model}).")

    print(f"Indexing eval/sample_data/ into KB '{GOLDEN_KB}'…")
    index_path(SAMPLE_DIR, table_name=GOLDEN_KB)

    print(f"\nEvaluating {len(items)} golden question(s) (top_k={top_k})…\n")
    rows = []
    for item in items:
        q = item["question"]
        gt = item.get("ground_truth", "")
        rel_sources = item.get("relevant_sources", [])

        with metrics.timed() as t_ret:
            context, sources = retrieve_with_sources(q, top_k=top_k, table_name=GOLDEN_KB)
        retrieved = _unique_sources(sources)

        with metrics.timed() as t_gen:
            answer = gen.generate(q, context, model=model)

        row = {
            "id": item.get("id"),
            "type": item.get("type", "factual"),
            "question": q,
            "answer": answer,
            "retrieved_sources": retrieved,
            "relevant_sources": rel_sources,
            "semantic_similarity": metrics.semantic_similarity(answer, gt),
            "answer_relevancy": metrics.answer_relevancy(answer, q),
            "lexical_faithfulness": metrics.lexical_faithfulness(answer, context),
            "context_recall": metrics.context_recall(retrieved, rel_sources) if rel_sources else None,
            "context_precision": metrics.context_precision(retrieved, rel_sources) if rel_sources else None,
            "retrieval_s": t_ret.seconds,
            "generation_s": t_gen.seconds,
        }
        rows.append(row)
        print(f"[{row['id']}] ({row['type']})  {q}")
        print(f"    answer: {answer.strip()[:160]}")
        print(f"    sources: {retrieved}  gold: {rel_sources}")
        print(
            f"    sim={fmt_num(row['semantic_similarity'])} "
            f"relevancy={fmt_num(row['answer_relevancy'])} "
            f"faithfulness={fmt_num(row['lexical_faithfulness'])} "
            f"ctx_recall={('n/a' if row['context_recall'] is None else fmt_pct(row['context_recall']))} "
            f"ctx_prec={('n/a' if row['context_precision'] is None else fmt_pct(row['context_precision']))}"
        )
        print(f"    latency: retrieve={row['retrieval_s']:.2f}s generate={row['generation_s']:.2f}s\n")

    with_ctx = [r for r in rows if r["context_recall"] is not None]
    aggregate = {
        "semantic_similarity": metrics.mean(r["semantic_similarity"] for r in rows),
        "answer_relevancy": metrics.mean(r["answer_relevancy"] for r in rows),
        "lexical_faithfulness": metrics.mean(r["lexical_faithfulness"] for r in rows),
        "context_recall": metrics.mean(r["context_recall"] for r in with_ctx),
        "context_precision": metrics.mean(r["context_precision"] for r in with_ctx),
        "avg_retrieval_s": metrics.mean(r["retrieval_s"] for r in rows),
        "avg_generation_s": metrics.mean(r["generation_s"] for r in rows),
        "n_items": len(rows),
        "top_k": top_k,
        "provider": gen.name,
        "model": model,
    }

    print("=" * 68)
    print("AGGREGATE (golden set)")
    print(f"  semantic_similarity : {fmt_num(aggregate['semantic_similarity'])}")
    print(f"  answer_relevancy    : {fmt_num(aggregate['answer_relevancy'])}")
    print(f"  lexical_faithfulness: {fmt_num(aggregate['lexical_faithfulness'])}")
    print(f"  context_recall      : {fmt_pct(aggregate['context_recall'])}")
    print(f"  context_precision   : {fmt_pct(aggregate['context_precision'])}")
    print(f"  avg latency         : retrieve {aggregate['avg_retrieval_s']:.2f}s / generate {aggregate['avg_generation_s']:.2f}s")

    payload = {"aggregate": aggregate, "results": rows}
    path = save_report("golden", payload, out=out)
    print(f"\nReport written to {path}")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Golden-set end-to-end RAG evaluation.")
    ap.add_argument("--top-k", type=int, default=4, help="Chunks retrieved per question.")
    ap.add_argument("--limit", type=int, default=None, help="Only evaluate the first N items.")
    ap.add_argument("--provider", type=str, default=None,
                    help="LLM provider to generate answers (default = configured provider).")
    ap.add_argument("--out", type=str, default=None, help="Explicit report output path.")
    args = ap.parse_args()
    run(top_k=args.top_k, limit=args.limit, out=args.out, provider=args.provider)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
