"""Test fixtures for ML Service."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from swen_ml.api.routes import accounts, classify, examples, health
from swen_ml.config.settings import Settings, get_settings


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def settings(temp_data_dir: Path) -> Settings:
    """Create test settings with temp storage."""
    return Settings(data_dir=temp_data_dir)


@pytest.fixture
def mock_encoder() -> MagicMock:
    """Create a mock encoder for unit tests."""
    encoder = MagicMock()
    encoder.dimension = 384
    encoder.encode.return_value = MagicMock()  # Mock numpy array
    return encoder


@pytest.fixture
def mock_nli() -> MagicMock:
    """Create a mock NLI classifier for unit tests."""
    nli = MagicMock()
    nli.classify.return_value = MagicMock()  # Mock scores array
    return nli


@pytest.fixture
def test_app(mock_encoder: MagicMock, mock_nli: MagicMock) -> FastAPI:
    """Create a test FastAPI app with mocked models."""
    app = FastAPI(title="SWEN ML Service (Test)")

    # Include routers
    app.include_router(health.router)
    app.include_router(classify.router)
    app.include_router(examples.router)
    app.include_router(accounts.router)

    # Set mocked app state
    app.state.encoder = mock_encoder
    app.state.nli = mock_nli

    return app


@pytest.fixture
def test_client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create a test client."""
    with TestClient(test_app) as client:
        yield client
