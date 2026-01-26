from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from ._utils import resolve_env_file_path


class Settings(BaseSettings):
    """ML service configuration."""

    log_level: str = "INFO"

    # Database config needs alias because the ML configs are usually
    # prefixed with SWEN_ML_ (see SettingsConfigDict). But the postgres
    # configs are shared with backend.
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

    # Data directory for evaluations
    data_dir: Path = Path("data")
    # For huggingface we need to use pooling and stuff
    encoder_backend: Literal["sentence-transformers", "huggingface"]
    encoder_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    # HuggingFace-specific options (ignored for sentence-transformers)
    encoder_pooling: Literal["mean", "cls", "max"] = "mean"
    encoder_normalize: bool = True
    encoder_max_length: int = 512
    device: str = "cpu"  # cuda, or mps -> untested!

    example_high_confidence: float = 0.85
    example_accept_threshold: float = 0.70
    example_margin_threshold: float = 0.10
    anchor_accept_threshold: float = 0.35
    noise_threshold: float = 0.30

    # Search enrichment
    enrichment_enabled: bool = True
    enrichment_searxng_url: str = "http://localhost:8888"
    enrichment_cache_ttl_days: int = 7
    enrichment_max_cache_size: int = 10000
    enrichment_search_timeout: float = 5.0
    enrichment_rate_limit_seconds: float = 1.0

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
