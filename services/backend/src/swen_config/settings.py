"""Application settings loaded from environment variables.

Configuration file discovery (in priority order):
1. OS environment variables (always highest priority)
2. SWEN_ENV_FILE environment variable (absolute path to .env file)
3. config/.env.dev - local development
4. config/.env - production/Docker

Uses pydantic-settings for automatic type coercion and validation.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import SecretStr, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root() -> Path:
    """Find the project root directory."""
    current = Path(__file__).resolve().parent

    for parent in [current, *current.parents]:
        if (parent / "config").is_dir():
            return parent
        if (parent / ".git").is_dir():
            return parent
        if parent == Path("/app"):
            return parent

    return Path(__file__).resolve().parents[4]


def get_config_dir() -> Path:
    """Get the config directory path (for fints_institute.csv, etc.)."""
    return _find_project_root() / "config"


def _resolve_env_file_path() -> Path | None:
    """Resolve the .env file path.

    Priority:
    1. SWEN_ENV_FILE env var (full path)
    2. config/.env.dev (local development)
    3. config/.env (production)
    """
    env_file_path = os.environ.get("SWEN_ENV_FILE")
    if env_file_path:
        path = Path(env_file_path)
        if not path.is_absolute():
            path = _find_project_root() / path
        if path.exists():
            return path

    config_dir = get_config_dir()

    dev_env = config_dir / ".env.dev"
    if dev_env.exists():
        return dev_env

    prod_env = config_dir / ".env"
    if prod_env.exists():
        return prod_env

    return None


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    Values are loaded from:
    1. OS environment variables (highest priority)
    2. .env file (config/.env.dev or config/.env)
    3. Default values
    """

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file_path(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Security (MUST be set - app fails without these)
    encryption_key: SecretStr  # Fernet key for encrypting stored credentials
    jwt_secret_key: SecretStr  # Secret for signing JWT tokens
    postgres_password: SecretStr  # Database password

    # Application
    app_name: str = "SWEN"
    debug: bool = False

    # Database (POSTGRES_ prefix)
    # Note: Databases are created via services/database/init-db.sql
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_db: str = "swen"

    # API (API_ prefix)
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    api_cors_origins: str = ""  # Empty = no CORS allowed (secure default)
    api_cookie_secure: bool = True  # Secure cookies by default
    api_cookie_samesite: Literal["lax", "strict", "none"] = "strict"
    api_cookie_domain: str | None = None
    api_trust_proxy_headers: bool = False

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def _validate_cors_origins(cls, v: Any) -> str:
        """Ensure cors_origins is stored as comma-separated string."""
        if isinstance(v, list):
            return ",".join(v)
        return str(v) if v else ""

    # JWT
    jwt_access_token_expire_hours: int = 1
    jwt_refresh_token_expire_days: int = 7

    # ML Service (for transaction classification)
    ml_service_enabled: bool = False
    ml_service_url: str = "http://localhost:8001"
    ml_service_timeout: float = 10.0

    # Banking
    fints_product_id: str = ""

    # Registration
    registration_mode: Literal["open", "admin_only"] = "admin_only"

    # SMTP (SMTP_ prefix)
    smtp_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr | None = None
    smtp_from_email: str = ""
    smtp_from_name: str = "SWEN"
    smtp_use_tls: bool = True
    smtp_starttls: bool = True

    # Frontend URL (for password reset links)
    frontend_base_url: str = "http://localhost:5173"

    # Logging (LOG_ prefix)
    log_level: str = "INFO"

    # Computed properties
    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Construct the database URL from components."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def database_type(self) -> str:
        """Database type (always postgresql now)."""
        return "postgresql"


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings.

    Required fields (encryption_key, jwt_secret_key, postgres_password)
    must be provided via environment variables or .env file.
    """
    return Settings()  # type: ignore[call-arg]  # pydantic-settings loads from env


def clear_settings_cache() -> None:
    """Clear the settings cache (useful for tests)."""
    get_settings.cache_clear()
