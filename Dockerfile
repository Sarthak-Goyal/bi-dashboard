# syntax=docker/dockerfile:1
# Single image: builds the React app, then serves it and the API from one FastAPI process.

# ── Stage 1: build the frontend ───────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

# Run as an unprivileged user (UID 10001) — never as root
RUN useradd --system --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown app:app /data

COPY --chown=app:app backend/app ./app
COPY --chown=app:app backend/healthcheck.py ./healthcheck.py
COPY --from=frontend --chown=app:app /build/dist ./static

ENV STATIC_DIR=/app/static \
    DATA_DIR=/data \
    ENVIRONMENT=production \
    PORT=8000

USER app
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "healthcheck.py"]

# One worker: the in-process scheduler and cache must not be duplicated.
# $PORT is honoured so the same image runs on Railway/Render/Fly.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
