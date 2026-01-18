"""Test fixtures for ML Service."""

import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from swen_ml import __version__
from swen_ml.config.settings import Settings
from swen_ml.inference.encoder import TransactionEncoder
from swen_ml.inference.similarity_classifier import SimilarityClassifier
from swen_ml.storage.embedding_store import EmbeddingStore
from swen_ml.api.routes import accounts, classify, examples, health, users


@pytest.fixture
def temp_storage_path() -> Generator[Path, None, None]:
    """Create a temporary directory for embedding storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def settings(temp_storage_path: Path) -> Settings:
    """Create test settings with temp storage."""
    return Settings(
        embedding_storage_path=temp_storage_path,
        hf_cache_path=temp_storage_path / "cache",
        similarity_threshold=0.70,
    )


@pytest.fixture
def embedding_store(temp_storage_path: Path) -> EmbeddingStore:
    """Create an embedding store with temp storage."""
    return EmbeddingStore(temp_storage_path)


# Note: The encoder fixture requires the actual model to be downloaded.
# For unit tests, we may want to mock the encoder.
# For integration tests, we use the real encoder.


@pytest.fixture
def encoder(settings: Settings) -> TransactionEncoder:
    """Create a real encoder (requires model download)."""
    # Use default HF cache to avoid permission issues
    return TransactionEncoder(
        model_name=settings.sentence_transformer_model,
        cache_folder=None,  # Use default HuggingFace cache
    )


@pytest.fixture
def classifier(
    encoder: TransactionEncoder,
    embedding_store: EmbeddingStore,
    settings: Settings,
) -> SimilarityClassifier:
    """Create a classifier with real encoder."""
    return SimilarityClassifier(
        encoder=encoder,
        store=embedding_store,
        similarity_threshold=settings.similarity_threshold,
    )


@pytest.fixture
def test_client(
    classifier: SimilarityClassifier,
    settings: Settings,
) -> Generator[TestClient, None, None]:
    """Create a test client with real classifier."""
    # Create app without lifespan to avoid double initialization
    app = FastAPI(
        title="SWEN ML Service (Test)",
        version=__version__,
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(classify.router)
    app.include_router(examples.router)
    app.include_router(accounts.router)
    app.include_router(users.router)

    # Set app state directly
    app.state.settings = settings
    app.state.classifier = classifier

    with TestClient(app) as client:
        yield client
