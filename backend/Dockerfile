FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/data/hf_cache \
    DATA_DIR=/data

WORKDIR /app

# System deps for pypdf / sentence-transformers wheels are already prebuilt;
# keep the image lean.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app

# Persistent volume mount point (SQLite + LanceDB + model cache live here).
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# Respect the platform-provided PORT (Render) or default to 8000 (Fly.io).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
