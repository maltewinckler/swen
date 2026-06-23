"""AI Model information value objects."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ModelStatus(Enum):
    """Status of an AI model in the registry."""

    AVAILABLE = "available"
    DOWNLOADING = "downloading"
    NOT_INSTALLED = "not_installed"


@dataclass(frozen=True)
class AIModelInfo:
    """Information about an AI model."""

    name: str
    display_name: str
    description: str
    size_bytes: int
    status: ModelStatus
    is_recommended: bool = True
    download_progress: Optional[float] = None

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
        return AIModelInfo(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            size_bytes=self.size_bytes,
            status=status,
            is_recommended=self.is_recommended,
            download_progress=download_progress,
        )

    def with_progress(self, progress: float) -> "AIModelInfo":
        return AIModelInfo(
            name=self.name,
            display_name=self.display_name,
            description=self.description,
            size_bytes=self.size_bytes,
            status=ModelStatus.DOWNLOADING,
            is_recommended=self.is_recommended,
            download_progress=max(0.0, min(1.0, progress)),
        )


@dataclass(frozen=True)
class DownloadProgress:
    """Progress update for a model download operation."""

    model_name: str
    status: str
    completed_bytes: int = 0
    total_bytes: int = 0
    progress: Optional[float] = None
    is_complete: bool = False
    error: Optional[str] = None

    @property
    def progress_percent(self) -> Optional[float]:
        if self.progress is not None:
            return self.progress * 100
        return None
