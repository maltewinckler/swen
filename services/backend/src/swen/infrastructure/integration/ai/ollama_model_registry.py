"""Ollama Model Registry implementation.

This module implements the AIModelRegistry interface for Ollama,
providing model management operations like listing, downloading,
and status checking.

The registry maintains a curated list of recommended models that
are known to work well with SWEN's transaction classification task.
"""

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import ClassVar

import httpx

from swen.domain.integration.ports import AIModelRegistry
from swen.domain.integration.value_objects import (
    AIModelInfo,
    DownloadProgress,
    ModelStatus,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelRecommendation:
    """A recommended model for SWEN."""

    name: str
    display_name: str
    description: str
    size_bytes: int
    is_primary: bool = False  # Only one model should be marked as primary recommended


class OllamaModelRegistry(AIModelRegistry):
    """Ollama implementation of AIModelRegistry."""

    # Curated models known to work well with SWEN
    # This list is Ollama-specific and maintained by the project
    RECOMMENDED_MODELS: ClassVar[dict[str, ModelRecommendation]] = {
        "qwen2.5:1.5b": ModelRecommendation(
            name="qwen2.5:1.5b",
            display_name="Qwen 2.5 (1.5B)",
            description="Fast, good for most transactions",
            size_bytes=1_000_000_000,
        ),
        "qwen2.5:3b": ModelRecommendation(
            name="qwen2.5:3b",
            display_name="Qwen 2.5 (3B)",
            description="Best balance of speed and accuracy",
            size_bytes=1_900_000_000,
            is_primary=True,  # This is the default recommended model
        ),
        "llama3.2:3b": ModelRecommendation(
            name="llama3.2:3b",
            display_name="Llama 3.2 (3B)",
            description="Good multilingual support",
            size_bytes=2_000_000_000,
        ),
        "mistral:7b": ModelRecommendation(
            name="mistral:7b",
            display_name="Mistral (7B)",
            description="Highest accuracy, requires more resources",
            size_bytes=4_100_000_000,
        ),
    }

    def __init__(self, base_url: str = "http://localhost:11434"):
        self._base_url = base_url.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def list_models(self) -> list[AIModelInfo]:
        installed_models = await self._get_installed_models()

        # Track which recommendations are already covered by installed models
        # Use exact match on "base:variant" format (e.g., qwen2.5:3b)
        covered_recommendations: set[str] = set()
        for model in installed_models:
            installed_name = model.name
            # Check if any recommendation matches this installed model
            for rec_name in self.RECOMMENDED_MODELS:
                if self._models_match(installed_name, rec_name):
                    covered_recommendations.add(rec_name)

        # Start with installed models
        result = list(installed_models)

        # Add recommended models that aren't covered by installed ones
        for name, rec in self.RECOMMENDED_MODELS.items():
            if name in covered_recommendations:
                continue

            result.append(
                AIModelInfo(
                    name=rec.name,
                    display_name=rec.display_name,
                    description=rec.description,
                    size_bytes=rec.size_bytes,
                    status=ModelStatus.NOT_INSTALLED,
                    is_recommended=rec.is_primary,
                ),
            )

        # Sort: recommended first, then available, then by name
        result.sort(
            key=lambda m: (
                not m.is_recommended,
                m.status != ModelStatus.AVAILABLE,
                m.name,
            ),
        )

        return result

    def _models_match(self, installed_name: str, recommended_name: str) -> bool:
        if installed_name == recommended_name:
            return True

        # Parse base:variant format
        installed_parts = installed_name.split(":", 1)
        rec_parts = recommended_name.split(":", 1)

        if len(installed_parts) < 2 or len(rec_parts) < 2:
            return False

        installed_base, installed_variant = installed_parts
        rec_base, rec_variant = rec_parts

        # Base must match exactly
        if installed_base != rec_base:
            return False

        # "latest" tag covers any recommended version of the same model
        if installed_variant == "latest":
            return True

        # Variant must start with the recommended variant
        # e.g., "7b-instruct-v0.3" starts with "7b"
        return installed_variant.startswith(rec_variant)

    async def get_model_info(self, model_name: str) -> AIModelInfo | None:
        # Check if installed (exact match)
        installed = await self._get_installed_models()
        for model in installed:
            if model.name == model_name:
                return model

        # Check if in recommended list
        rec = self.RECOMMENDED_MODELS.get(model_name)
        if rec:
            return AIModelInfo(
                name=rec.name,
                display_name=rec.display_name,
                description=rec.description,
                size_bytes=rec.size_bytes,
                status=ModelStatus.NOT_INSTALLED,
                is_recommended=True,
            )

        return None

    async def pull_model(self, model_name: str) -> AsyncIterator[DownloadProgress]:
        logger.info("Starting download of model '%s'", model_name)

        try:
            # Use a long timeout - model downloads can take minutes
            timeout = httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0)

            async with (
                httpx.AsyncClient(timeout=timeout) as client,
                client.stream(
                    "POST",
                    f"{self._base_url}/api/pull",
                    json={"name": model_name},
                ) as response,
            ):
                if response.status_code != 200:
                    yield DownloadProgress(
                        model_name=model_name,
                        status="error",
                        error=f"HTTP {response.status_code}",
                    )
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        progress = self._parse_progress(model_name, data)
                        yield progress

                        if progress.is_complete or progress.error:
                            return

                    except json.JSONDecodeError:
                        continue

            # Final success message
            yield DownloadProgress(
                model_name=model_name,
                status="success",
                is_complete=True,
            )

        except httpx.TimeoutException:
            logger.error("Model download timed out: %s", model_name)
            yield DownloadProgress(
                model_name=model_name,
                status="error",
                error="Download timed out",
            )
        except httpx.ConnectError:
            logger.error("Could not connect to Ollama at %s", self._base_url)
            yield DownloadProgress(
                model_name=model_name,
                status="error",
                error=f"Could not connect to Ollama at {self._base_url}",
            )
        except Exception as e:
            logger.error("Model download failed: %s", str(e))
            yield DownloadProgress(
                model_name=model_name,
                status="error",
                error=str(e),
            )

    async def is_model_available(self, model_name: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                if response.status_code != 200:
                    return False

                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]

                return any(
                    model_name in model or model.startswith(model_name.split(":")[0])
                    for model in models
                )

        except Exception:
            return False

    async def is_healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def _get_installed_models(self) -> list[AIModelInfo]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                if response.status_code != 200:
                    return []

                data = response.json()
                models = []

                for model_data in data.get("models", []):
                    name = model_data.get("name", "")
                    size = model_data.get("size", 0)

                    # Check if this is a recommended model
                    rec = self._find_recommendation(name)

                    models.append(
                        AIModelInfo(
                            name=name,
                            display_name=rec.display_name if rec else name,
                            description=rec.description if rec else "Custom model",
                            size_bytes=size,
                            status=ModelStatus.AVAILABLE,
                            is_recommended=rec.is_primary if rec else False,
                        ),
                    )

                return models

        except Exception as e:
            logger.warning("Failed to fetch installed models: %s", str(e))
            return []

    def _find_recommendation(self, model_name: str) -> ModelRecommendation | None:
        # Direct match
        if model_name in self.RECOMMENDED_MODELS:
            return self.RECOMMENDED_MODELS[model_name]

        # Check if model name starts with a recommended model
        for rec_name, rec in self.RECOMMENDED_MODELS.items():
            if model_name.startswith(rec_name.split(":")[0]):
                return rec

        return None

    def _parse_progress(self, model_name: str, data: dict) -> DownloadProgress:
        status = data.get("status", "")
        error = data.get("error")

        if error:
            return DownloadProgress(
                model_name=model_name,
                status="error",
                error=error,
            )

        if status == "success":
            return DownloadProgress(
                model_name=model_name,
                status="success",
                is_complete=True,
            )

        total = data.get("total", 0)
        completed = data.get("completed", 0)
        progress = (completed / total) if total > 0 else None

        return DownloadProgress(
            model_name=model_name,
            status=status,
            completed_bytes=completed,
            total_bytes=total,
            progress=progress,
        )
