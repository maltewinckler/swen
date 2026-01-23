"""Application settings."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ML service configuration."""

    # Logging
    log_level: str = "INFO"

    # Paths
    data_dir: Path = Path("data")

    # Embedding model (using sentence-transformers compatible model)
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = 384

    # NLI model
    nli_model: str = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"

    # Classification thresholds
    example_high_confidence: float = 0.85
    example_accept_threshold: float = 0.70
    example_margin_threshold: float = 0.10
    anchor_accept_threshold: float = 0.55
    nli_accept_threshold: float = 0.70
    nli_margin_threshold: float = 0.15

    # Noise model
    noise_threshold: float = 0.30

    # Cache
    max_cached_users: int = 100

    model_config = {"env_prefix": "SWEN_ML_"}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
