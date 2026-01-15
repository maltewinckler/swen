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

# Install Poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VERSION=2.1.4
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# Copy dependency files first (better caching)
COPY services/backend/pyproject.toml services/backend/poetry.lock ./

# Configure Poetry: no virtualenv, install to system
ENV POETRY_VIRTUALENVS_CREATE=false

# Install dependencies (includes public git dependency `geldstrom` via HTTPS)
RUN poetry install --only main --no-interaction --no-ansi --no-root

# Copy source code
COPY services/backend/src/swen ./src/swen
COPY services/backend/src/swen_identity ./src/swen_identity
COPY services/backend/src/swen_config ./src/swen_config

# Install the project itself
RUN poetry install --only main --no-interaction --no-ansi

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

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app/src/swen /app/src/swen
COPY --from=builder /app/src/swen_identity /app/src/swen_identity
COPY --from=builder /app/src/swen_config /app/src/swen_config

# Set Python path
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
