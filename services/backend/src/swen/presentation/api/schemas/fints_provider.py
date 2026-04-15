"""Schemas for FinTS provider management endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SaveGeldstromApiConfigRequest(BaseModel):
    """Request to save Geldstrom API configuration."""

    api_key: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Geldstrom API key (Bearer token)",
    )
    endpoint_url: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Geldstrom API base URL",
    )


class ActivateProviderRequest(BaseModel):
    """Request to activate a FinTS provider."""

    mode: str = Field(
        ...,
        pattern="^(local|api)$",
        description="Provider to activate: 'local' or 'api'",
    )


class GeldstromApiConfigResponse(BaseModel):
    """Geldstrom API configuration details."""

    api_key_masked: str
    endpoint_url: str
    is_active: bool
    last_updated: Optional[datetime] = None
    last_updated_by: Optional[str] = None


class FintsProviderStatusResponse(BaseModel):
    """Overall FinTS provider status."""

    local_configured: bool
    local_active: bool
    api_configured: bool
    api_active: bool
    active_provider: Optional[str] = None
