"""Tests for OllamaModelRegistry."""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from swen.domain.integration.value_objects import (
    DownloadProgress,
    ModelStatus,
)
from swen.infrastructure.integration.ai import OllamaModelRegistry


@pytest.fixture
def registry() -> OllamaModelRegistry:
    """Default registry instance."""
    return OllamaModelRegistry(base_url="http://localhost:11434")


class TestOllamaModelRegistryInit:
    """Tests for registry initialization."""

    def test_default_initialization(self):
        """Test default registry settings."""
        registry = OllamaModelRegistry()

        assert registry.provider_name == "ollama"
        assert registry._base_url == "http://localhost:11434"

    def test_custom_base_url(self):
        """Test custom base URL."""
        registry = OllamaModelRegistry(base_url="http://192.168.1.100:11434")

        assert registry._base_url == "http://192.168.1.100:11434"

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base URL."""
        registry = OllamaModelRegistry(base_url="http://localhost:11434/")

        assert registry._base_url == "http://localhost:11434"


class TestRecommendedModels:
    """Tests for recommended models configuration."""

    def test_has_recommended_models(self):
        """Test that RECOMMENDED_MODELS contains curated models."""
        assert len(OllamaModelRegistry.RECOMMENDED_MODELS) > 0

    def test_recommended_models_structure(self):
        """Test that recommended models have correct structure."""
        for name, rec in OllamaModelRegistry.RECOMMENDED_MODELS.items():
            assert rec.name == name
            assert rec.display_name
            assert rec.description
            assert rec.size_bytes > 0

    def test_exactly_one_primary_model(self):
        """Test that exactly one model is marked as primary."""
        primary_count = sum(
            1 for rec in OllamaModelRegistry.RECOMMENDED_MODELS.values() if rec.is_primary
        )
        assert primary_count == 1

    def test_qwen_is_primary(self):
        """Test that qwen2.5:3b is the primary recommended model."""
        primary = next(
            rec
            for rec in OllamaModelRegistry.RECOMMENDED_MODELS.values()
            if rec.is_primary
        )
        assert "qwen" in primary.name.lower()


class TestModelMatching:
    """Tests for model name matching logic."""

    def test_exact_match(self, registry):
        """Test exact model name match."""
        assert registry._models_match("qwen2.5:3b", "qwen2.5:3b") is True

    def test_variant_match(self, registry):
        """Test variant suffix match (e.g., 7b-instruct-v0.3 matches 7b)."""
        assert registry._models_match("mistral:7b-instruct-v0.3", "mistral:7b") is True

    def test_latest_matches_any_variant(self, registry):
        """Test that 'latest' tag matches any recommended variant."""
        assert registry._models_match("qwen2.5:latest", "qwen2.5:3b") is True
        assert registry._models_match("mistral:latest", "mistral:7b") is True

    def test_different_base_no_match(self, registry):
        """Test that different base names don't match."""
        assert registry._models_match("llama3.2:3b", "qwen2.5:3b") is False

    def test_different_size_variants_no_match(self, registry):
        """Test that different size variants don't match."""
        # 1.5b and 3b are different variants
        assert registry._models_match("qwen2.5:1.5b", "qwen2.5:3b") is False

    def test_missing_variant_no_match(self, registry):
        """Test that incomplete names don't match."""
        assert registry._models_match("qwen2.5", "qwen2.5:3b") is False


class TestListModels:
    """Tests for listing models."""

    @pytest.mark.asyncio
    async def test_list_models_empty_installed(self, registry):
        """Test listing when no models are installed."""
        mock_response = httpx.Response(200, json={"models": []})

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            models = await registry.list_models()

        # Should return all recommended models with NOT_INSTALLED status
        assert len(models) >= len(OllamaModelRegistry.RECOMMENDED_MODELS)
        for model in models:
            assert model.status == ModelStatus.NOT_INSTALLED

    @pytest.mark.asyncio
    async def test_list_models_with_installed(self, registry):
        """Test listing with some installed models."""
        mock_response = httpx.Response(
            200,
            json={
                "models": [
                    {"name": "qwen2.5:3b", "size": 1_900_000_000},
                    {"name": "custom-model:latest", "size": 500_000_000},
                ]
            },
        )

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            models = await registry.list_models()

        # Find installed models
        installed = [m for m in models if m.status == ModelStatus.AVAILABLE]
        assert len(installed) >= 2

        # Check that qwen2.5:3b is marked available
        qwen_model = next((m for m in models if m.name == "qwen2.5:3b"), None)
        assert qwen_model is not None
        assert qwen_model.status == ModelStatus.AVAILABLE
        assert qwen_model.is_recommended is True  # Is primary recommended

    @pytest.mark.asyncio
    async def test_list_models_connection_error(self, registry):
        """Test listing when Ollama is not reachable."""
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            models = await registry.list_models()

        # Should still return recommended models (as not_installed)
        assert len(models) == len(OllamaModelRegistry.RECOMMENDED_MODELS)
        for model in models:
            assert model.status == ModelStatus.NOT_INSTALLED

    @pytest.mark.asyncio
    async def test_list_models_sorting(self, registry):
        """Test that models are sorted: recommended first, then available, then name."""
        mock_response = httpx.Response(
            200,
            json={
                "models": [
                    {"name": "zz-custom:latest", "size": 100_000_000},
                    {"name": "qwen2.5:3b", "size": 1_900_000_000},
                ]
            },
        )

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            models = await registry.list_models()

        # Primary recommended should be first
        assert models[0].is_recommended is True


class TestGetModelInfo:
    """Tests for getting specific model info."""

    @pytest.mark.asyncio
    async def test_get_installed_model(self, registry):
        """Test getting info for an installed model."""
        mock_response = httpx.Response(
            200,
            json={
                "models": [
                    {"name": "qwen2.5:3b", "size": 1_900_000_000},
                ]
            },
        )

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            model = await registry.get_model_info("qwen2.5:3b")

        assert model is not None
        assert model.name == "qwen2.5:3b"
        assert model.status == ModelStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_get_recommended_not_installed(self, registry):
        """Test getting info for a recommended but not installed model."""
        mock_response = httpx.Response(200, json={"models": []})

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            model = await registry.get_model_info("qwen2.5:3b")

        assert model is not None
        assert model.name == "qwen2.5:3b"
        assert model.status == ModelStatus.NOT_INSTALLED
        assert model.is_recommended is True

    @pytest.mark.asyncio
    async def test_get_unknown_model(self, registry):
        """Test getting info for an unknown model."""
        mock_response = httpx.Response(200, json={"models": []})

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            model = await registry.get_model_info("unknown-model:latest")

        assert model is None


class TestIsModelAvailable:
    """Tests for checking model availability."""

    @pytest.mark.asyncio
    async def test_model_available(self, registry):
        """Test when model is installed."""
        mock_response = httpx.Response(
            200,
            json={"models": [{"name": "qwen2.5:3b"}]},
        )

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await registry.is_model_available("qwen2.5:3b")

        assert result is True

    @pytest.mark.asyncio
    async def test_model_not_available(self, registry):
        """Test when model is not installed."""
        mock_response = httpx.Response(200, json={"models": []})

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await registry.is_model_available("qwen2.5:3b")

        assert result is False

    @pytest.mark.asyncio
    async def test_model_available_connection_error(self, registry):
        """Test when Ollama is not reachable."""
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            result = await registry.is_model_available("qwen2.5:3b")

        assert result is False


class TestIsHealthy:
    """Tests for health check."""

    @pytest.mark.asyncio
    async def test_healthy(self, registry):
        """Test when Ollama is healthy."""
        mock_response = httpx.Response(200, json={"models": []})

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await registry.is_healthy()

        assert result is True

    @pytest.mark.asyncio
    async def test_unhealthy_bad_status(self, registry):
        """Test when Ollama returns error status."""
        mock_response = httpx.Response(500)

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await registry.is_healthy()

        assert result is False

    @pytest.mark.asyncio
    async def test_unhealthy_connection_error(self, registry):
        """Test when Ollama is not reachable."""
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            result = await registry.is_healthy()

        assert result is False


class TestPullModel:
    """Tests for model download."""

    @pytest.mark.asyncio
    async def test_pull_model_success(self, registry):
        """Test successful model download with progress updates."""
        # Simulate streaming response lines
        progress_lines = [
            json.dumps({"status": "pulling manifest"}),
            json.dumps({"status": "downloading", "completed": 500_000_000, "total": 1_000_000_000}),
            json.dumps({"status": "downloading", "completed": 1_000_000_000, "total": 1_000_000_000}),
            json.dumps({"status": "success"}),
        ]

        class MockStreamResponse:
            status_code = 200

            async def aiter_lines(self):
                for line in progress_lines:
                    yield line

        class MockStreamContextManager:
            async def __aenter__(self):
                return MockStreamResponse()

            async def __aexit__(self, *args):
                pass

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, *args, **kwargs):
                return MockStreamContextManager()

        with patch("httpx.AsyncClient", return_value=MockClient()):
            progress_updates = []
            async for progress in registry.pull_model("qwen2.5:3b"):
                progress_updates.append(progress)

        assert len(progress_updates) >= 2
        # Last update should be complete
        assert progress_updates[-1].is_complete is True
        assert progress_updates[-1].error is None

    @pytest.mark.asyncio
    async def test_pull_model_with_progress_percentage(self, registry):
        """Test that download progress is calculated correctly."""
        progress_lines = [
            json.dumps({"status": "downloading", "completed": 250_000_000, "total": 1_000_000_000}),
        ]

        class MockStreamResponse:
            status_code = 200

            async def aiter_lines(self):
                for line in progress_lines:
                    yield line

        class MockStreamContextManager:
            async def __aenter__(self):
                return MockStreamResponse()

            async def __aexit__(self, *args):
                pass

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, *args, **kwargs):
                return MockStreamContextManager()

        with patch("httpx.AsyncClient", return_value=MockClient()):
            progress_updates = []
            async for progress in registry.pull_model("qwen2.5:3b"):
                progress_updates.append(progress)

        # Should have at least one downloading progress and a final success
        assert len(progress_updates) >= 1
        # Find the downloading progress (not the final success)
        downloading_progress = next(
            (p for p in progress_updates if p.status == "downloading"),
            None,
        )
        assert downloading_progress is not None
        assert downloading_progress.progress == 0.25
        assert downloading_progress.completed_bytes == 250_000_000
        assert downloading_progress.total_bytes == 1_000_000_000

    @pytest.mark.asyncio
    async def test_pull_model_error_in_response(self, registry):
        """Test handling error in download response."""
        progress_lines = [
            json.dumps({"status": "pulling manifest"}),
            json.dumps({"error": "model not found"}),
        ]

        class MockStreamResponse:
            status_code = 200

            async def aiter_lines(self):
                for line in progress_lines:
                    yield line

        class MockStreamContextManager:
            async def __aenter__(self):
                return MockStreamResponse()

            async def __aexit__(self, *args):
                pass

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, *args, **kwargs):
                return MockStreamContextManager()

        with patch("httpx.AsyncClient", return_value=MockClient()):
            progress_updates = []
            async for progress in registry.pull_model("invalid-model"):
                progress_updates.append(progress)

        # Last update should have error
        assert progress_updates[-1].error is not None
        assert "not found" in progress_updates[-1].error

    @pytest.mark.asyncio
    async def test_pull_model_http_error(self, registry):
        """Test handling HTTP error during download."""

        class MockStreamResponse:
            status_code = 500

        class MockStreamContextManager:
            async def __aenter__(self):
                return MockStreamResponse()

            async def __aexit__(self, *args):
                pass

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, *args, **kwargs):
                return MockStreamContextManager()

        with patch("httpx.AsyncClient", return_value=MockClient()):
            progress_updates = []
            async for progress in registry.pull_model("qwen2.5:3b"):
                progress_updates.append(progress)

        assert len(progress_updates) == 1
        assert progress_updates[0].error is not None
        assert "HTTP 500" in progress_updates[0].error

    @pytest.mark.asyncio
    async def test_pull_model_connection_error(self, registry):
        """Test handling connection error during download."""

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, *args, **kwargs):
                raise httpx.ConnectError("Connection refused")

        with patch("httpx.AsyncClient", return_value=MockClient()):
            progress_updates = []
            async for progress in registry.pull_model("qwen2.5:3b"):
                progress_updates.append(progress)

        assert len(progress_updates) == 1
        assert progress_updates[0].error is not None
        assert "connect" in progress_updates[0].error.lower()

    @pytest.mark.asyncio
    async def test_pull_model_timeout_error(self, registry):
        """Test handling timeout during download."""

        class MockClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            def stream(self, *args, **kwargs):
                raise httpx.TimeoutException("Request timed out")

        with patch("httpx.AsyncClient", return_value=MockClient()):
            progress_updates = []
            async for progress in registry.pull_model("qwen2.5:3b"):
                progress_updates.append(progress)

        assert len(progress_updates) == 1
        assert progress_updates[0].error is not None
        assert "timed out" in progress_updates[0].error.lower()


class TestParseProgress:
    """Tests for progress parsing helper."""

    def test_parse_progress_success(self, registry):
        """Test parsing success status."""
        data = {"status": "success"}
        progress = registry._parse_progress("qwen2.5:3b", data)

        assert progress.status == "success"
        assert progress.is_complete is True
        assert progress.error is None

    def test_parse_progress_with_bytes(self, registry):
        """Test parsing progress with byte counts."""
        data = {
            "status": "downloading",
            "completed": 500_000_000,
            "total": 1_000_000_000,
        }
        progress = registry._parse_progress("qwen2.5:3b", data)

        assert progress.status == "downloading"
        assert progress.completed_bytes == 500_000_000
        assert progress.total_bytes == 1_000_000_000
        assert progress.progress == 0.5

    def test_parse_progress_with_error(self, registry):
        """Test parsing error response."""
        data = {"error": "Something went wrong"}
        progress = registry._parse_progress("qwen2.5:3b", data)

        assert progress.status == "error"
        assert progress.error == "Something went wrong"

    def test_parse_progress_zero_total(self, registry):
        """Test parsing progress when total is 0 (unknown)."""
        data = {
            "status": "initializing",
            "completed": 0,
            "total": 0,
        }
        progress = registry._parse_progress("qwen2.5:3b", data)

        assert progress.progress is None


class TestFindRecommendation:
    """Tests for finding recommendations."""

    def test_find_exact_match(self, registry):
        """Test finding recommendation by exact name."""
        rec = registry._find_recommendation("qwen2.5:3b")
        assert rec is not None
        assert rec.name == "qwen2.5:3b"

    def test_find_partial_match(self, registry):
        """Test finding recommendation by base name."""
        # mistral:7b-instruct should match mistral:7b
        rec = registry._find_recommendation("mistral:7b-instruct")
        assert rec is not None
        assert "mistral" in rec.name

    def test_find_no_match(self, registry):
        """Test when no recommendation matches."""
        rec = registry._find_recommendation("unknown-model:latest")
        assert rec is None

