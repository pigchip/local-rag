"""Run the full evaluation suite (golden set + BEIR retrieval) and summarize.

Everything is free/local. BEIR requires the optional ``datasets`` package; if it
is missing the retrieval layer is skipped with a clear notice.

Run from the ``backend/`` directory::

    .venv/Scripts/python.exe -m eval.run_all
    .venv/Scripts/python.exe -m eval.run_all --golden-limit 3 --beir-sample 50 --max-corpus 2000
"""

from __future__ import annotations

import argparse

from eval.data import BEIR_DATASETS
from eval.report import fmt_num, fmt_pct, save_report
from eval.run_golden import run as run_golden


def main() -> int:
    ap = argparse.ArgumentParser(description="Full RAG evaluation suite.")
    ap.add_argument("--top-k", type=int, default=4)
    ap.add_argument("--golden-limit", type=int, default=None)
    ap.add_argument("--provider", type=str, default=None,
                    help="LLM provider for the golden set (default = configured provider).")
    ap.add_argument("--datasets", nargs="+", default=list(BEIR_DATASETS), choices=list(BEIR_DATASETS))
    ap.add_argument("--beir-sample", type=int, default=None)
    ap.add_argument("--max-corpus", type=int, default=None)
    ap.add_argument("--reuse-index", action="store_true")
    ap.add_argument("--skip-beir", action="store_true", help="Only run the golden set.")
    args = ap.parse_args()

    print("#" * 68)
    print("# GOLDEN SET (end-to-end generation)")
    print("#" * 68)
    golden = run_golden(top_k=args.top_k, limit=args.golden_limit, out=None, provider=args.provider)

    beir = None
    if not args.skip_beir:
        print("\n" + "#" * 68)
        print("# BEIR (retrieval)")
        print("#" * 68)
        try:
            from eval.run_beir import run as run_beir

            beir = run_beir(
                args.datasets, top_k=max(args.top_k, 10), sample=args.beir_sample,
                max_corpus=args.max_corpus, reuse=args.reuse_index, out=None,
            )
        except ImportError as exc:
            print(f"\n[skipped] BEIR retrieval: {exc}")

    print("\n" + "=" * 68)
    print("SUITE SUMMARY")
    print("=" * 68)
    g = golden["aggregate"]
    print("Golden set:")
    print(f"  semantic_similarity={fmt_num(g['semantic_similarity'])} "
          f"faithfulness={fmt_num(g['lexical_faithfulness'])} "
          f"ctx_recall={fmt_pct(g['context_recall'])}")
    if beir:
        for name, agg in beir["results"].items():
            print(f"BEIR {name}: Recall@10={fmt_pct(agg['recall@10'])} "
                  f"nDCG@10={fmt_num(agg['ndcg@10'])} MRR={fmt_num(agg['mrr'])}")

    save_report("suite", {"golden": golden.get("aggregate"),
                          "beir": beir["results"] if beir else None})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
