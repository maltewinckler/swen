"""ML Service configuration."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ML_SERVICE_ROOT = Path(__file__).parent.parent.parent
_REPO_ROOT = _ML_SERVICE_ROOT.parent.parent


def _get_env_file() -> str | None:
    if env_file := os.environ.get("SWEN_ENV_FILE"):
        return env_file
    if (p := _REPO_ROOT / "config" / ".env.dev").exists():
        return str(p)
    if (p := _REPO_ROOT / "config" / ".env").exists():
        return str(p)
    return None


class Settings(BaseSettings):
    # Storage
    embedding_storage_path: Path = _ML_SERVICE_ROOT / "data" / "embeddings"
    hf_cache_path: Path = _ML_SERVICE_ROOT / "data" / "cache"

    # Model
    sentence_transformer_model: str = "distiluse-base-multilingual-cased-v2"
    embedding_dim: int = 512

    # Classification thresholds
    similarity_threshold: float = 0.70
    description_threshold: float = 0.45
    max_examples_per_account: int = 100

    # API
    api_prefix: str = ""
    debug: bool = False

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=_get_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )
