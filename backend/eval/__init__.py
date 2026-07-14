"""Local RAG evaluation suite (dev-only — not shipped in any deployment image).

Console-runnable, 100% free/local evaluation of the RAG stack (Haystack + LanceDB
+ the app's provider registry). Three layers:

* a shipped **golden set** over ``eval/sample_data/`` (end-to-end + generation metrics),
* a **retrieval benchmark** over small BEIR datasets (SciFact, NFCorpus),
* **judge-free generation metrics** (embedding similarity, lexical faithfulness,
  context recall/precision) — no external judge required.

Run modules from the ``backend/`` directory with the project venv, e.g.::

    .venv/Scripts/python.exe -m eval.run_golden --limit 3
    .venv/Scripts/python.exe -m eval.run_beir --datasets scifact --sample 50
    .venv/Scripts/python.exe -m eval.run_all

This package is intentionally excluded from the Docker image (the Dockerfiles copy
only ``app/``) and no runtime code imports it.
"""
