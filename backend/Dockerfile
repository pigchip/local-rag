FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf_cache \
    DATA_DIR=/data

WORKDIR /app

# System deps for pypdf / sentence-transformers wheels are already prebuilt;
# keep the image lean.
COPY requirements.txt .
# Install the CPU-only PyTorch build first so sentence-transformers doesn't pull
# the default CUDA wheels (~7 GB of unused GPU libs). Keeps the image ~1.8 GB.
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install -r requirements.txt

# Bake the local embedding model into the image (into HF_HOME, which lives
# OUTSIDE the /data runtime volume) so the first query needs no network download.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY app ./app

# Persistent volume mount point (SQLite + LanceDB live here).
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# Respect the platform-provided PORT (Render) or default to 8000 (Fly.io).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
