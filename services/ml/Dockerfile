# SWEN ML Service Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (for better caching)
COPY pyproject.toml uv.lock ./
COPY services/contracts ./services/contracts
COPY services/ml/pyproject.toml ./services/ml/

# Install dependencies (without the local packages yet)
RUN uv sync --frozen --no-install-workspace --package swen-ml

# Copy source code
COPY services/ml/swen_ml ./services/ml/swen_ml

# Install the workspace packages
RUN uv sync --frozen --package swen-ml

# Create data directories
RUN mkdir -p /app/data/cache /app/data/embeddings

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV EMBEDDING_STORAGE_PATH=/app/data/embeddings
ENV HF_HOME=/app/data/cache

# Expose port
EXPOSE 8100

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8100/health || exit 1

# Run the application
CMD ["uvicorn", "swen_ml.api.app:app", "--host", "0.0.0.0", "--port", "8100"]
