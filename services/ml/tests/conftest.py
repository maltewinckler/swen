"""Test fixtures for ML Service."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from swen_ml import __version__
from swen_ml.api.routes import accounts, classify, examples, health, users
from swen_ml.config.settings import Settings
from swen_ml.inference.anchors import AnchorManager, AnchorTextBuilder
from swen_ml.inference.encoding import EncoderFactory, TransactionEncoder
from swen_ml.inference.example_manager import ExampleManager
from swen_ml.inference.pipeline import ClassificationPipeline
from swen_ml.storage.anchor_store import AnchorStore
from swen_ml.storage.embedding_store import EmbeddingStore


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


@pytest.fixture
def anchor_store(temp_storage_path: Path) -> AnchorStore:
    """Create an anchor store with temp storage."""
    return AnchorStore(temp_storage_path)


# Note: The encoder fixture requires the actual model to be downloaded.
# For unit tests, we may want to mock the encoder.
# For integration tests, we use the real encoder.


@pytest.fixture
def encoder(settings: Settings) -> TransactionEncoder:
    """Create a real encoder (requires model download)."""
    return EncoderFactory.create(
        encoder_id=settings.encoder,
        cache_folder=None,  # Use default HuggingFace cache
    )


@pytest.fixture
def pipeline(
    encoder: TransactionEncoder,
    embedding_store: EmbeddingStore,
    anchor_store: AnchorStore,
    settings: Settings,
) -> ClassificationPipeline:
    """Create a classification pipeline with real encoder."""
    return ClassificationPipeline(
        encoder=encoder,
        store=embedding_store,
        anchor_store=anchor_store,
        settings=settings,
    )


@pytest.fixture
def example_manager(
    encoder: TransactionEncoder,
    embedding_store: EmbeddingStore,
    settings: Settings,
) -> ExampleManager:
    """Create an example manager with real encoder."""
    return ExampleManager(
        encoder=encoder,
        store=embedding_store,
        max_examples_per_account=settings.max_examples_per_account,
    )


@pytest.fixture
def test_client(
    pipeline: ClassificationPipeline,
    example_manager: ExampleManager,
    embedding_store: EmbeddingStore,
    anchor_store: AnchorStore,
    settings: Settings,
) -> Generator[TestClient, None, None]:
    """Create a test client with real pipeline."""
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
    app.state.store = embedding_store
    app.state.anchor_store = anchor_store
    app.state.pipeline = pipeline
    app.state.example_manager = example_manager
    app.state.anchor_manager = AnchorManager(
        encoder=app.state.pipeline._encoder,  # noqa: SLF001 - tests
        store=anchor_store,
        builder=AnchorTextBuilder(variant=settings.anchor_variant),  # type: ignore[arg-type]
        encoder_id=settings.encoder,
    )

    with TestClient(app) as client:
        yield client
