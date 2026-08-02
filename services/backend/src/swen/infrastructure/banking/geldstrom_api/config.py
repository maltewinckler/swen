"""Transfer objects for Geldstrom API configuration."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GeldstromApiConfig(BaseModel):
    """Represents system-wide Geldstrom API configuration.

    DTO for transferring configuration data between
    infrastructure and application layers.
    """

    model_config = ConfigDict(frozen=True)

    api_key: str  # Decrypted
    endpoint_url: str
    is_active: bool = False
    created_at: datetime = Field(default_factory=_utc_now)
    created_by_id: str = ""
    updated_at: datetime = Field(default_factory=_utc_now)
    updated_by_id: str = ""


class GeldstromApiConfigStatus(BaseModel):
    """Configuration status for display and validation."""

    model_config = ConfigDict(frozen=True)

    is_configured: bool
    is_active: bool = False
    endpoint_url: str | None = None
