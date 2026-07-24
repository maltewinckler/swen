"""Schemas for FinTS provider management endpoints."""

from pydantic import BaseModel, ConfigDict, Field

from swen.application.system.queries import (
    FintsProviderStatusDTO,
    GeldstromApiConfigDTO,
)


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


class GeldstromApiConfigResponse(GeldstromApiConfigDTO):
    """Geldstrom API configuration details."""

    model_config = ConfigDict(from_attributes=True)


class FintsProviderStatusResponse(FintsProviderStatusDTO):
    """Overall FinTS provider status."""

    model_config = ConfigDict(from_attributes=True)
