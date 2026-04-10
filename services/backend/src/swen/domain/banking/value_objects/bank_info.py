"""Bank information value object with public metadata of a bank."""

from pydantic import BaseModel, ConfigDict, Field


class BankInfo(BaseModel):
    """Immutable public metadata for a bank identified by BLZ.

    This is a pure domain concept representing publicly available
    bank information. It does NOT include FinTS endpoint URLs or
    other infrastructure-specific details.
    """

    blz: str = Field(
        ...,
        min_length=8,
        max_length=8,
        description="Bankleitzahl (8-digit German bank code)",
    )
    name: str = Field(..., min_length=1, description="Bank name")
    bic: str | None = Field(default=None, description="BIC/SWIFT code")
    organization: str | None = Field(
        default=None,
        description="Parent organization or banking group",
    )
    is_fints_capable: bool = Field(
        default=True,
        description="Whether this bank supports FinTS",
    )

    model_config = ConfigDict(frozen=True)
