# SWEN Backend Dockerfile
# Multi-stage build with hardened slim runtime

# ============================================
# Stage 1: Build dependencies
# ============================================
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy workspace root files and dependency files (for workspace dependencies)
COPY pyproject.toml uv.lock ./
COPY services/contracts ./services/contracts
COPY services/backend/pyproject.toml ./services/backend/

# Install dependencies (without the local packages yet)
RUN uv sync --frozen --no-dev --no-install-workspace --package swen-backend

# Copy source code
COPY services/backend/src/swen ./services/backend/src/swen
COPY services/backend/src/swen_identity ./services/backend/src/swen_identity
COPY services/backend/src/swen_config ./services/backend/src/swen_config

# Install the workspace packages
RUN uv sync --frozen --no-dev --package swen-backend

# ============================================
# Stage 2: Hardened Slim Runtime
# ============================================
FROM python:3.13-slim AS runtime

WORKDIR /app

# Install only curl for healthcheck, then clean up
# Create non-root user for security
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 65532 nonroot \
    && useradd --uid 65532 --gid nonroot --shell /usr/sbin/nologin --create-home nonroot

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/services/backend/src/swen /app/src/swen
COPY --from=builder /app/services/backend/src/swen_identity /app/src/swen_identity
COPY --from=builder /app/services/backend/src/swen_config /app/src/swen_config

# Copy workspace dependency (contracts) - needed for workspace packages
COPY --from=builder /app/services/contracts /app/services/contracts

# Set Python path and add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create data and config directories
RUN mkdir -p /app/data /app/config && chown -R nonroot:nonroot /app/data /app/config

# Switch to non-root user
USER nonroot

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/health || exit 1

# Default command: run the API server
CMD ["python", "-m", "uvicorn", "swen.presentation.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
