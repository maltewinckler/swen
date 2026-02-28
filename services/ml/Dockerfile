# SWEN ML Service Dockerfile
# Multi-stage build with slim runtime

# ============================================
# Stage 1: Build dependencies
# ============================================
FROM python:3.13-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /uvx /bin/

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock ./
COPY services/contracts ./services/contracts
COPY services/ml/pyproject.toml ./services/ml/

# Install dependencies
RUN uv sync --frozen --no-dev --no-install-workspace --package swen-ml
# Then copy source code
COPY services/ml/swen_ml ./services/ml/swen_ml
# Then quickly install local packages
RUN uv sync --frozen --no-dev --package swen-ml

# ============================================
# Stage 2: Slim runtime
# ============================================
FROM python:3.13-slim AS runtime

# only have this as a fallback for local builds. CI uses GH tag
ARG VERSION=dev

WORKDIR /app

# Install only curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 65532 nonroot \
    && useradd --uid 65532 --gid nonroot --shell /usr/sbin/nologin --create-home nonroot

# Copy the virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/services/ml/swen_ml /app/swen_ml
COPY --from=builder /app/services/contracts /app/services/contracts

# Create data directories and hand off to non-root user
RUN mkdir -p /app/data/cache /app/data/embeddings \
    && chown -R nonroot:nonroot /app/data

USER nonroot

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app
ENV EMBEDDING_STORAGE_PATH=/app/data/embeddings
ENV HF_HOME=/app/data/cache

LABEL org.opencontainers.image.title="swen-ml" \
      org.opencontainers.image.description="SWEN ML Classification Service" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="https://github.com/maltewinckler/swen"

EXPOSE 8100

CMD ["uvicorn", "swen_ml.api.app:app", "--host", "0.0.0.0", "--port", "8100"]
