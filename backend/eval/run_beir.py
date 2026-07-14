"""Retrieval benchmark over small BEIR datasets (SciFact, NFCorpus).

Indexes each dataset's corpus into an isolated eval KB, runs every (sampled)
query through our retriever, and computes standard IR metrics against the qrels.
Retrieval only — no LLM generation involved.

Run from the ``backend/`` directory::

    .venv/Scripts/python.exe -m eval.run_beir                              # scifact + nfcorpus
    .venv/Scripts/python.exe -m eval.run_beir --datasets scifact --sample 50 --max-corpus 2000
"""

from __future__ import annotations

import argparse

from eval import metrics
from eval.data import BEIR_DATASETS, load_beir
from eval.indexing import index_corpus, retrieve_doc_ids
from eval.report import fmt_num, fmt_pct, save_report

K_VALUES = (5, 10)


def evaluate_dataset(
    name: str,
    top_k: int,
    sample: int | None,
    max_corpus: int | None,
    reuse: bool,
) -> dict:
    print(f"\n=== BEIR: {name} ===")
    corpus, queries, qrels = load_beir(
        name, num_queries=sample, max_corpus=max_corpus
    )
    print(f"  corpus={len(corpus)} queries={len(queries)} judged={len(qrels)}")

    table = f"eval_{name}"
    print(f"  indexing corpus into KB '{table}' (reuse={reuse})…")
    n = index_corpus(corpus, table, reuse=reuse)
    print(f"  indexed {n} document(s).")

    per_query = {f"recall@{k}": [] for k in K_VALUES}
    per_query.update({f"precision@{k}": [] for k in K_VALUES})
    per_query["ndcg@10"] = []
    per_query["mrr"] = []
    latencies = []

    for qid, text in queries.items():
        rel = qrels.get(qid, {})
        if not rel:
            continue
        with metrics.timed() as t:
            ranked = retrieve_doc_ids(text, table, top_k=max(top_k, max(K_VALUES)))
        latencies.append(t.seconds)
        for k in K_VALUES:
            per_query[f"recall@{k}"].append(metrics.recall_at_k(ranked, rel, k))
            per_query[f"precision@{k}"].append(metrics.precision_at_k(ranked, rel, k))
        per_query["ndcg@10"].append(metrics.ndcg_at_k(ranked, rel, 10))
        per_query["mrr"].append(metrics.mrr(ranked, rel))

    agg = {metric: metrics.mean(vals) for metric, vals in per_query.items()}
    agg["avg_retrieval_s"] = metrics.mean(latencies)
    agg["n_queries"] = len(latencies)
    agg["corpus_size"] = len(corpus)

    print(f"  Recall@5 ={fmt_pct(agg['recall@5'])}  Recall@10={fmt_pct(agg['recall@10'])}")
    print(f"  nDCG@10  ={fmt_num(agg['ndcg@10'])}  MRR      ={fmt_num(agg['mrr'])}")
    print(f"  Prec@5   ={fmt_pct(agg['precision@5'])}  Prec@10  ={fmt_pct(agg['precision@10'])}")
    print(f"  avg retrieval latency: {agg['avg_retrieval_s']:.3f}s over {agg['n_queries']} queries")
    return agg


def run(datasets: list[str], top_k: int, sample: int | None, max_corpus: int | None, reuse: bool, out: str | None) -> dict:
    results = {}
    for name in datasets:
        results[name] = evaluate_dataset(name, top_k, sample, max_corpus, reuse)
    payload = {"datasets": datasets, "sample": sample, "max_corpus": max_corpus, "results": results}
    path = save_report("beir", payload, out=out)
    print(f"\nReport written to {path}")
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="BEIR retrieval benchmark (SciFact/NFCorpus).")
    ap.add_argument("--datasets", nargs="+", default=list(BEIR_DATASETS),
                    choices=list(BEIR_DATASETS), help="Which BEIR datasets to evaluate.")
    ap.add_argument("--top-k", type=int, default=10, help="Chunks retrieved per query.")
    ap.add_argument("--sample", type=int, default=None, help="Limit to the first N judged queries.")
    ap.add_argument("--max-corpus", type=int, default=None,
                    help="Cap corpus size (relevant docs always kept) for faster CPU runs.")
    ap.add_argument("--reuse-index", action="store_true",
                    help="Reuse an already-indexed eval KB instead of re-embedding.")
    ap.add_argument("--out", type=str, default=None, help="Explicit report output path.")
    args = ap.parse_args()
    run(args.datasets, args.top_k, args.sample, args.max_corpus, args.reuse_index, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
