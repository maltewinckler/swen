"""Transfer objects for Geldstrom API configuration."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class GeldstromApiConfig:
    """Represents system-wide Geldstrom API configuration.

    DTO for transferring configuration data between
    infrastructure and application layers.
    """

    api_key: str  # Decrypted
    endpoint_url: str
    is_active: bool = False
    created_at: datetime = field(default_factory=_utc_now)
    created_by_id: str = ""
    updated_at: datetime = field(default_factory=_utc_now)
    updated_by_id: str = ""


@dataclass(frozen=True)
class GeldstromApiConfigStatus:
    """Configuration status for display and validation."""

    is_configured: bool
    is_active: bool = False
    endpoint_url: str | None = None
