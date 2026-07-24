"""DTOs for local FinTS configuration API endpoints."""

from pydantic import BaseModel, ConfigDict, computed_field

from swen.application.system.queries import FinTSConfigDTO, FinTSConfigStatusDTO


class FinTSConfigResponse(FinTSConfigDTO):
    """Local FinTS configuration details."""

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def csv_file_size_kb(self) -> int:
        return self.csv_file_size_bytes // 1024


class ConfigStatusResponse(FinTSConfigStatusDTO):
    """Local FinTS configuration status."""

    model_config = ConfigDict(from_attributes=True)


class UpdateLocalFinTSConfigResponse(BaseModel):
    """Response after creating or updating local FinTS configuration."""

    message: str
    institute_count: int | None = None
    file_size_kb: int | None = None
