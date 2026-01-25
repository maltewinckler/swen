"""Application settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ._utils import resolve_env_file_path


class Settings(BaseSettings):
    """ML service configuration."""

    # Logging
    log_level: str = "INFO"

    # Database - constructed from POSTGRES_* vars (shared with backend)
    postgres_host: str = Field(validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: str = Field(validation_alias="POSTGRES_PASSWORD")
    database_echo: bool = False

    @property
    def database_url(self) -> str:
        """Construct database URL from postgres settings."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/swen_ml"
        )

    # Data directory for evaluation (datasets, CLI experiments)
    data_dir: Path = Path("data")

    # Backend: "sentence-transformers" (recommended) or "huggingface" (experimental)
    encoder_backend: Literal["sentence-transformers", "huggingface"] = (
        "sentence-transformers"
    )

    # Model name from HuggingFace Hub
    # For sentence-transformers: "paraphrase-multilingual-MiniLM-L12-v2"
    # For huggingface: "answerdotai/ModernBERT-base"
    encoder_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # HuggingFace-specific options (ignored for sentence-transformers)
    encoder_pooling: Literal["mean", "cls", "max"] = "mean"
    encoder_normalize: bool = True
    encoder_max_length: int = 512

    # -------------------------------------------------------------------------
    # NLI Model
    # -------------------------------------------------------------------------
    nli_model: str = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"

    # Device for ML models (cpu, cuda, mps)
    device: str = "cpu"

    # -------------------------------------------------------------------------
    # Classification Thresholds
    # -------------------------------------------------------------------------
    example_high_confidence: float = 0.85
    example_accept_threshold: float = 0.70
    example_margin_threshold: float = 0.10
    anchor_accept_threshold: float = 0.35
    nli_accept_threshold: float = 0.70
    nli_margin_threshold: float = 0.15

    # Noise model
    noise_threshold: float = 0.30

    # -------------------------------------------------------------------------
    # Search Enrichment (tier_3)
    # -------------------------------------------------------------------------
    enrichment_enabled: bool = True
    enrichment_searxng_url: str = "http://localhost:8888"
    enrichment_cache_ttl_days: int = 7
    enrichment_max_cache_size: int = 10000
    enrichment_search_timeout: float = 5.0
    enrichment_rate_limit_seconds: float = 1.0

    # Cache
    max_cached_users: int = 100

    model_config = SettingsConfigDict(
        env_file=resolve_env_file_path(),
        env_file_encoding="utf-8",
        env_prefix="SWEN_ML_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]  # pydantic-settings fills from env
