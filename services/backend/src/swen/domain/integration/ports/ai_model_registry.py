"""AI Model Registry port (interface)."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from swen.domain.integration.value_objects import AIModelInfo, DownloadProgress


class AIModelRegistry(ABC):
    """
    Abstract interface for AI model management operations.

    This port defines the contract for managing AI models used in
    counter-account resolution. Implementations handle provider-specific
    details (Ollama, OpenAI, etc.).

    Responsibilities:
    - List available and installed models
    - Download new models with progress tracking
    - Check model and service health

    Usage in Application Layer:
        >>> registry = OllamaModelRegistry(base_url="http://localhost:11434")
        >>> models = await registry.list_models()
        >>> async for progress in registry.pull_model("qwen2.5:3b"):
        ...     print(f"Download: {progress.progress_percent}%")
    """

    @abstractmethod
    async def list_models(self) -> list[AIModelInfo]:
        """
        List all available models (installed and recommended).

        Returns
        -------
        List of AIModelInfo objects sorted by:
        1. Status (available first, then not_installed)
        2. Name alphabetically
        """

    @abstractmethod
    async def get_model_info(self, model_name: str) -> AIModelInfo | None:
        """
        Get information about a specific model.

        Parameters
        ----------
        model_name
            Model identifier (e.g., "qwen2.5:3b")

        Returns
        -------
        AIModelInfo if the model is known, None otherwise
        """

    @abstractmethod
    def pull_model(self, model_name: str) -> AsyncIterator[DownloadProgress]:
        """
        Download a model with streaming progress updates.

        This is an async generator that yields progress updates as the
        model downloads. The final yield will have is_complete=True.

        Parameters
        ----------
        model_name
            Model identifier to download (e.g., "qwen2.5:3b")

        Yields
        ------
        DownloadProgress objects with status updates
        """

    @abstractmethod
    async def is_model_available(self, model_name: str) -> bool:
        """
        Check if a specific model is installed and ready to use.

        Parameters
        ----------
        model_name
            Model identifier to check

        Returns
        -------
        True if model is installed and available, False otherwise
        """

    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Check if the AI backend service is reachable and healthy.

        Returns
        -------
        True if the service is responding, False otherwise
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Name of the AI provider (e.g., "ollama", "openai").

        Used for logging and display purposes.
        """
