# --- Single-container image for Hugging Face Spaces (Docker SDK) ---
# Stage 1 builds the Vite SPA; stage 2 runs FastAPI, which serves both the API
# (/api/*) and the compiled frontend from one origin on $PORT (7860 on Spaces).

FROM node:22-alpine AS web
WORKDIR /web
# Empty VITE_API_BASE_URL => the SPA calls the API on the same origin (/api).
ENV VITE_API_BASE_URL=""
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf_cache \
    DATA_DIR=/data \
    FRONTEND_DIST=/app/static \
    PORT=7860

WORKDIR /app

COPY backend/requirements.txt .
# Install the CPU-only PyTorch build first so sentence-transformers doesn't pull
# the default CUDA wheels (~7 GB of unused GPU libs). Keeps the image ~1.8 GB.
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install -r requirements.txt

# Bake the local embedding model into the image (into HF_HOME, which lives
# OUTSIDE the /data runtime volume) so the first query needs no network download.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY backend/app ./app
# Compiled SPA served by FastAPI (see app/main.py static mount).
COPY --from=web /web/dist ./static

# Runtime data (SQLite + LanceDB + model cache). On HF free Spaces this is
# ephemeral, so persistence.py mirrors it to a HF Dataset when configured.
RUN mkdir -p /data && chmod -R 777 /data

EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
