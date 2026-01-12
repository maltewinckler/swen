"""Bank credentials value object."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from swen.domain.shared.value_objects.secure_string import SecureString


class BankCredentials(BaseModel):
    """
    Value object representing bank login credentials.

    For FinTS/HBCI, this includes:
    - BLZ (Bankleitzahl) - German bank code
    - Username/Login ID (secured)
    - PIN (secured)
    - Endpoint URL (optional, can be derived from BLZ)

    Security:
    - Username and PIN are SecureStrings to prevent accidental logging
    """

    blz: str = Field(
        ...,
        min_length=8,
        max_length=8,
        description="Bankleitzahl",
    )
    username: SecureString = Field(..., description="Login ID")
    pin: SecureString = Field(..., description="PIN for authentication")
    endpoint: str = Field(..., min_length=1, description="FinTS endpoint URL")

    model_config = ConfigDict(frozen=True)

    @field_validator("blz")
    @classmethod
    def validate_blz(cls, v: str) -> str:
        if not v.isdigit():
            msg = "BLZ must contain only digits"
            raise ValueError(msg)
        return v

    def __repr__(self) -> str:
        return (
            f"BankCredentials(blz={self.blz}, username=*****, "
            f"pin=*****, endpoint={self.endpoint})"
        )

    def __str__(self) -> str:
        return f"BankCredentials(blz={self.blz}, endpoint={self.endpoint})"

    @classmethod
    def from_plain(
        cls,
        blz: str,
        username: str,
        pin: str,
        endpoint: str,
    ) -> "BankCredentials":
        """Create BankCredentials from plain strings."""
        return cls(
            blz=blz,
            username=SecureString(username),
            pin=SecureString(pin),
            endpoint=endpoint,
        )

    @classmethod
    def from_env(cls, blz: str, endpoint: str) -> "BankCredentials":
        """Create BankCredentials from environment variables (testing..)."""
        return cls(
            blz=blz,
            username=SecureString.from_env("FINTS_USERNAME"),
            pin=SecureString.from_env("FINTS_PIN"),
            endpoint=endpoint,
        )
