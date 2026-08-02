"""AI Model information value objects."""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class ModelStatus(Enum):
    """Status of an AI model in the registry."""

    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    NOT_INSTALLED = "not_installed"


class AIModelInfo(BaseModel):
    """Information about an AI model."""

    model_config = ConfigDict(frozen=True)

    name: str
    display_name: str
    description: str
    size_bytes: int
    status: ModelStatus
    is_recommended: bool = True
    download_progress: float | None = None

    @property
    def size_display(self) -> str:
        if self.size_bytes >= 1_000_000_000:
            return f"{self.size_bytes / 1_000_000_000:.1f} GB"
        if self.size_bytes >= 1_000_000:
            return f"{self.size_bytes / 1_000_000:.1f} MB"
        return f"{self.size_bytes / 1_000:.1f} KB"

    def with_status(self, status: ModelStatus) -> "AIModelInfo":
        download_progress = (
            None if status != ModelStatus.DOWNLOADING else self.download_progress
        )
        return self.model_copy(
            update={"status": status, "download_progress": download_progress}
        )

    def with_progress(self, progress: float) -> "AIModelInfo":
        return self.model_copy(
            update={
                "status": ModelStatus.DOWNLOADING,
                "download_progress": max(0.0, min(1.0, progress)),
            }
        )


class DownloadProgress(BaseModel):
    """Progress update for a model download operation."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    status: str
    completed_bytes: int = 0
    total_bytes: int = 0
    progress: float | None = None
    is_complete: bool = False
    error: str | None = None

    @property
    def progress_percent(self) -> float | None:
        if self.progress is not None:
            return self.progress * 100
        return None
