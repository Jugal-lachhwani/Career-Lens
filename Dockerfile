# ============================================================
# CareerLens — Dockerfile
# Multi-stage, non-root, production-ready
# ============================================================

# ---------- Stage 1: builder (compile wheels) ---------------
FROM python:3.11-slim AS builder

WORKDIR /build

# System deps needed to compile psycopg2 and cryptography wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        build-essential \
        libffi-dev \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build all wheels into /wheels so the runtime stage can install without gcc
RUN pip install --upgrade pip && \
    pip wheel --default-timeout=1000 --no-cache-dir --wheel-dir=/wheels -r requirements.txt


# ---------- Stage 2: runtime --------------------------------
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system libs only (libpq for psycopg2 at runtime; no compiler needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install pre-built wheels — fast, no compiler required
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# Copy application source
COPY . .

# Create non-root user (security best practice)
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/logs /app/job_descriptions \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Liveness / readiness check (Docker will mark container unhealthy after 3 fails)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command: FastAPI with multi-process Uvicorn
# UVICORN_WORKERS can be overridden via docker-compose environment:
CMD ["sh", "-c", "uvicorn src.api:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers ${UVICORN_WORKERS:-4} \
        --timeout-keep-alive 120"]
