"""Tests for AI Model info value objects."""

import pytest

from swen.domain.integration.value_objects import (
    AIModelInfo,
    DownloadProgress,
    ModelStatus,
)


class TestModelStatus:
    """Test cases for ModelStatus enum."""

    def test_available_status(self):
        """Test AVAILABLE status value."""
        assert ModelStatus.AVAILABLE.value == "available"

    def test_downloading_status(self):
        """Test DOWNLOADING status value."""
        assert ModelStatus.DOWNLOADING.value == "downloading"

    def test_not_installed_status(self):
        """Test NOT_INSTALLED status value."""
        assert ModelStatus.NOT_INSTALLED.value == "not_installed"

    def test_all_statuses_exist(self):
        """Test that all expected statuses exist."""
        statuses = list(ModelStatus)
        assert len(statuses) == 3
        assert ModelStatus.AVAILABLE in statuses
        assert ModelStatus.DOWNLOADING in statuses
        assert ModelStatus.NOT_INSTALLED in statuses


class TestAIModelInfo:
    """Test cases for AIModelInfo value object."""

    def test_create_available_model(self):
        """Test creating an available model info."""
        model = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5 (3B)",
            description="Best balance of speed and accuracy",
            size_bytes=1_900_000_000,
            status=ModelStatus.AVAILABLE,
        )

        assert model.name == "qwen2.5:3b"
        assert model.display_name == "Qwen 2.5 (3B)"
        assert model.description == "Best balance of speed and accuracy"
        assert model.size_bytes == 1_900_000_000
        assert model.status == ModelStatus.AVAILABLE
        assert model.is_recommended is True  # Default
        assert model.download_progress is None

    def test_create_not_installed_model(self):
        """Test creating a not installed model info."""
        model = AIModelInfo(
            name="mistral:7b",
            display_name="Mistral (7B)",
            description="Highest accuracy",
            size_bytes=4_100_000_000,
            status=ModelStatus.NOT_INSTALLED,
            is_recommended=False,
        )

        assert model.status == ModelStatus.NOT_INSTALLED
        assert model.is_recommended is False

    def test_create_downloading_model(self):
        """Test creating a downloading model info."""
        model = AIModelInfo(
            name="llama3.2:3b",
            display_name="Llama 3.2 (3B)",
            description="Good multilingual support",
            size_bytes=2_000_000_000,
            status=ModelStatus.DOWNLOADING,
            download_progress=0.45,
        )

        assert model.status == ModelStatus.DOWNLOADING
        assert model.download_progress == 0.45


class TestAIModelInfoSizeDisplay:
    """Test cases for AIModelInfo size_display property."""

    def test_size_display_gigabytes(self):
        """Test size display for models in GB range."""
        model = AIModelInfo(
            name="test:1b",
            display_name="Test",
            description="Test",
            size_bytes=1_900_000_000,
            status=ModelStatus.AVAILABLE,
        )

        assert model.size_display == "1.9 GB"

    def test_size_display_megabytes(self):
        """Test size display for models in MB range."""
        model = AIModelInfo(
            name="test:tiny",
            display_name="Test",
            description="Test",
            size_bytes=500_000_000,
            status=ModelStatus.AVAILABLE,
        )

        assert model.size_display == "500.0 MB"

    def test_size_display_kilobytes(self):
        """Test size display for small files in KB range."""
        model = AIModelInfo(
            name="test:micro",
            display_name="Test",
            description="Test",
            size_bytes=500_000,
            status=ModelStatus.AVAILABLE,
        )

        assert model.size_display == "500.0 KB"

    def test_size_display_large_model(self):
        """Test size display for large 7B+ models."""
        model = AIModelInfo(
            name="mistral:7b",
            display_name="Mistral",
            description="Test",
            size_bytes=4_100_000_000,
            status=ModelStatus.AVAILABLE,
        )

        assert model.size_display == "4.1 GB"


class TestAIModelInfoWithStatus:
    """Test cases for AIModelInfo with_status method."""

    def test_with_status_to_available(self):
        """Test changing status to AVAILABLE."""
        original = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5",
            description="Fast model",
            size_bytes=1_900_000_000,
            status=ModelStatus.NOT_INSTALLED,
        )

        updated = original.with_status(ModelStatus.AVAILABLE)

        assert updated.status == ModelStatus.AVAILABLE
        # Other fields unchanged
        assert updated.name == original.name
        assert updated.display_name == original.display_name
        assert updated.description == original.description
        assert updated.size_bytes == original.size_bytes

    def test_with_status_clears_progress_when_not_downloading(self):
        """Test that progress is cleared when status is not DOWNLOADING."""
        original = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5",
            description="Fast model",
            size_bytes=1_900_000_000,
            status=ModelStatus.DOWNLOADING,
            download_progress=0.75,
        )

        updated = original.with_status(ModelStatus.AVAILABLE)

        assert updated.status == ModelStatus.AVAILABLE
        assert updated.download_progress is None

    def test_with_status_keeps_progress_when_downloading(self):
        """Test that progress is kept when status is DOWNLOADING."""
        original = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5",
            description="Fast model",
            size_bytes=1_900_000_000,
            status=ModelStatus.DOWNLOADING,
            download_progress=0.5,
        )

        updated = original.with_status(ModelStatus.DOWNLOADING)

        assert updated.status == ModelStatus.DOWNLOADING
        assert updated.download_progress == 0.5

    def test_with_status_preserves_is_recommended(self):
        """Test that is_recommended is preserved."""
        original = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5",
            description="Fast model",
            size_bytes=1_900_000_000,
            status=ModelStatus.NOT_INSTALLED,
            is_recommended=True,
        )

        updated = original.with_status(ModelStatus.AVAILABLE)

        assert updated.is_recommended is True


class TestAIModelInfoWithProgress:
    """Test cases for AIModelInfo with_progress method."""

    def test_with_progress_sets_status_to_downloading(self):
        """Test that with_progress sets status to DOWNLOADING."""
        original = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5",
            description="Fast model",
            size_bytes=1_900_000_000,
            status=ModelStatus.NOT_INSTALLED,
        )

        updated = original.with_progress(0.25)

        assert updated.status == ModelStatus.DOWNLOADING
        assert updated.download_progress == 0.25

    def test_with_progress_clamps_to_zero(self):
        """Test that progress is clamped to minimum 0.0."""
        original = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5",
            description="Fast model",
            size_bytes=1_900_000_000,
            status=ModelStatus.NOT_INSTALLED,
        )

        updated = original.with_progress(-0.5)

        assert updated.download_progress == 0.0

    def test_with_progress_clamps_to_one(self):
        """Test that progress is clamped to maximum 1.0."""
        original = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5",
            description="Fast model",
            size_bytes=1_900_000_000,
            status=ModelStatus.NOT_INSTALLED,
        )

        updated = original.with_progress(1.5)

        assert updated.download_progress == 1.0

    def test_with_progress_preserves_other_fields(self):
        """Test that other fields are preserved."""
        original = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5",
            description="Fast model",
            size_bytes=1_900_000_000,
            status=ModelStatus.NOT_INSTALLED,
            is_recommended=True,
        )

        updated = original.with_progress(0.5)

        assert updated.name == original.name
        assert updated.display_name == original.display_name
        assert updated.description == original.description
        assert updated.size_bytes == original.size_bytes
        assert updated.is_recommended == original.is_recommended


class TestAIModelInfoImmutability:
    """Test immutability of AIModelInfo."""

    def test_immutable(self):
        """Test that AIModelInfo is frozen/immutable."""
        model = AIModelInfo(
            name="qwen2.5:3b",
            display_name="Qwen 2.5",
            description="Fast model",
            size_bytes=1_900_000_000,
            status=ModelStatus.AVAILABLE,
        )

        with pytest.raises(AttributeError):
            model.name = "changed"  # type: ignore


class TestDownloadProgress:
    """Test cases for DownloadProgress value object."""

    def test_create_minimal_progress(self):
        """Test creating progress with minimal fields."""
        progress = DownloadProgress(
            model_name="qwen2.5:3b",
            status="pulling manifest",
        )

        assert progress.model_name == "qwen2.5:3b"
        assert progress.status == "pulling manifest"
        assert progress.completed_bytes == 0
        assert progress.total_bytes == 0
        assert progress.progress is None
        assert progress.is_complete is False
        assert progress.error is None

    def test_create_progress_with_bytes(self):
        """Test creating progress with byte counts."""
        progress = DownloadProgress(
            model_name="qwen2.5:3b",
            status="downloading",
            completed_bytes=500_000_000,
            total_bytes=1_000_000_000,
            progress=0.5,
        )

        assert progress.completed_bytes == 500_000_000
        assert progress.total_bytes == 1_000_000_000
        assert progress.progress == 0.5

    def test_create_completed_progress(self):
        """Test creating completed progress."""
        progress = DownloadProgress(
            model_name="qwen2.5:3b",
            status="success",
            is_complete=True,
        )

        assert progress.is_complete is True
        assert progress.error is None

    def test_create_error_progress(self):
        """Test creating progress with error."""
        progress = DownloadProgress(
            model_name="qwen2.5:3b",
            status="error",
            error="Model not found",
        )

        assert progress.error == "Model not found"
        assert progress.is_complete is False


class TestDownloadProgressPercent:
    """Test cases for DownloadProgress progress_percent property."""

    def test_progress_percent_with_value(self):
        """Test progress_percent when progress is set."""
        progress = DownloadProgress(
            model_name="qwen2.5:3b",
            status="downloading",
            progress=0.75,
        )

        assert progress.progress_percent == 75.0

    def test_progress_percent_zero(self):
        """Test progress_percent when progress is zero."""
        progress = DownloadProgress(
            model_name="qwen2.5:3b",
            status="downloading",
            progress=0.0,
        )

        assert progress.progress_percent == 0.0

    def test_progress_percent_full(self):
        """Test progress_percent when progress is 100%."""
        progress = DownloadProgress(
            model_name="qwen2.5:3b",
            status="downloading",
            progress=1.0,
        )

        assert progress.progress_percent == 100.0

    def test_progress_percent_none_when_progress_none(self):
        """Test progress_percent returns None when progress is None."""
        progress = DownloadProgress(
            model_name="qwen2.5:3b",
            status="initializing",
        )

        assert progress.progress_percent is None


class TestDownloadProgressImmutability:
    """Test immutability of DownloadProgress."""

    def test_immutable(self):
        """Test that DownloadProgress is frozen/immutable."""
        progress = DownloadProgress(
            model_name="qwen2.5:3b",
            status="downloading",
        )

        with pytest.raises(AttributeError):
            progress.status = "changed"  # type: ignore

    def test_hashable(self):
        """Test that DownloadProgress can be used in sets."""
        progress1 = DownloadProgress(
            model_name="qwen2.5:3b",
            status="downloading",
        )
        progress2 = DownloadProgress(
            model_name="llama3.2:3b",
            status="downloading",
        )

        progress_set = {progress1, progress2}
        assert len(progress_set) == 2

    def test_equality(self):
        """Test equality comparison."""
        progress1 = DownloadProgress(
            model_name="qwen2.5:3b",
            status="downloading",
            progress=0.5,
        )
        progress2 = DownloadProgress(
            model_name="qwen2.5:3b",
            status="downloading",
            progress=0.5,
        )

        assert progress1 == progress2

