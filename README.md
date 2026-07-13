# Local RAG

A retrieval-augmented chat app with a **Vite + React + TypeScript + Tailwind
(shadcn/ui)** frontend and a **FastAPI** backend that reuses a local **Haystack +
LanceDB** retrieval pipeline. Answer generation is provider-swappable (Groq,
Google Gemini, OpenRouter, Hugging Face Inference, or a fully-local HuggingFace
model). Embeddings and retrieval always run locally.

## Features

- **Session history** — chats persist in SQLite; browse, resume, rename, delete.
- **Knowledge bases (KBs)** — each KB is an isolated LanceDB table.
  - Create a new KB from one or many files (PDF, TXT, Markdown, code).
  - Upload individual or batch files into an existing KB.
  - Every KB gets an **auto-generated one-line description** to tell them apart.
  - Manage a KB: list indexed files, delete a file, or clear the KB.
- **Grounded answers with citations** — inline `[n]` markers plus expandable
  source excerpts and scores.
- **Streaming** — token-by-token responses over **SSE**, with a stop button.
- **Swappable providers** — pick provider + model at runtime; only the selected
  provider's API key is required.

## Architecture

```
frontend (Vite/React)  ──REST + SSE──►  backend (FastAPI)
                                          ├─ retrieval: Haystack + LanceDB (local embeddings)
                                          ├─ generation: Groq | Gemini | OpenRouter | HF | local
                                          └─ persistence: SQLite (sessions, messages, kb_meta)
```

## Repository layout

| Path | Role |
| --- | --- |
| `backend/app/core/` | Config, logging, ported Haystack/LanceDB pipeline. |
| `backend/app/llm/` | Provider abstraction + adapters + registry. |
| `backend/app/db/` | SQLite schema + repository. |
| `backend/app/services/` | KB service (create/describe) + chat orchestration. |
| `backend/app/api/` | REST + SSE routers (`kb`, `sessions`, `providers`). |
| `frontend/src/` | React app (sidebar, chat, KB dialogs, API hooks). |

## Run locally

### 1. Backend (Python 3.11+)

```bash
cd backend
python -m venv .venv
# Windows:  .\.venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then set LLM_PROVIDER + the matching API key
uvicorn app.main:app --reload --port 8000
```

Get a **free** key for your chosen provider:

- Groq: https://console.groq.com/keys
- Google Gemini: https://aistudio.google.com/apikey
- OpenRouter (has `:free` models): https://openrouter.ai/keys
- Hugging Face: https://huggingface.co/settings/tokens

To run generation **fully offline**, set `LLM_PROVIDER=local` and uncomment the
`transformers` / `torch` lines in `backend/requirements.txt`.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_BASE_URL=http://localhost:8000
npm run dev                   # http://localhost:5173
```

### Or with Docker Compose

```bash
GROQ_API_KEY=... docker compose up --build   # backend on :8000
```

## API overview

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness check. |
| `GET` | `/api/providers` | Providers, models, configured status. |
| `GET` | `/api/kb` | List KBs with descriptions + stats. |
| `POST` | `/api/kb` | Create KB from uploaded files (multipart). |
| `GET` | `/api/kb/{kb}/files` | List indexed files. |
| `POST` | `/api/kb/{kb}/files` | Add files to a KB (multipart). |
| `DELETE` | `/api/kb/{kb}/files?file_path=…` | Delete one file. |
| `DELETE` | `/api/kb/{kb}` | Clear a KB. |
| `GET/POST` | `/api/sessions` | List / create sessions. |
| `GET/PATCH/DELETE` | `/api/sessions/{id}` | Read / update / delete a session. |
| `POST` | `/api/sessions/{id}/messages` | Send a query; **SSE** stream of tokens + sources. |

## Deploy (free tiers)

Recommended: **Fly.io** (backend, no sleep + persistent volume) + **Cloudflare
Pages** (frontend). Render / Vercel work too.

### Backend → Fly.io

```bash
cd backend
fly launch --no-deploy                      # edit app name in fly.toml first
fly volume create ragdata --size 3 --region iad
fly secrets set LLM_PROVIDER=groq GROQ_API_KEY=... \
                CORS_ORIGINS=https://your-frontend.pages.dev
fly deploy
```

The `[[mounts]]` volume at `/data` keeps SQLite + LanceDB across restarts.

### Backend → Render (alternative)

Create a **Web Service** from `backend/` (Docker), add a **1 GB persistent
disk** mounted at `/data`, set `DATA_DIR=/data` and your provider secrets. Note:
the free tier sleeps after idle.

### Frontend → Cloudflare Pages

- Build command: `npm run build`  ·  Output dir: `dist`  ·  Root: `frontend`
- Env var: `VITE_API_BASE_URL=https://<your-backend-url>`
- SPA routing is handled by `frontend/public/_redirects` (Vercel: `vercel.json`).

Set the backend's `CORS_ORIGINS` to your deployed frontend origin.
