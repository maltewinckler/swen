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

    model_config = ConfigDict(frozen=True)

    @field_validator("blz")
    @classmethod
    def validate_blz(cls, v: str) -> str:
        if not v.isdigit():
            msg = "BLZ must contain only digits"
            raise ValueError(msg)
        return v

    def __repr__(self) -> str:
        return f"BankCredentials(blz={self.blz}, username=*****, pin=*****)"

    def __str__(self) -> str:
        return f"BankCredentials(blz={self.blz})"

    @classmethod
    def from_plain(
        cls,
        blz: str,
        username: str,
        pin: str,
    ) -> "BankCredentials":
        """Create BankCredentials from plain strings."""
        return cls(
            blz=blz,
            username=SecureString(username),
            pin=SecureString(pin),
        )

    @classmethod
    def from_env(cls, blz: str) -> "BankCredentials":
        """Create BankCredentials from environment variables (testing)."""
        return cls(
            blz=blz,
            username=SecureString.from_env("FINTS_USERNAME"),
            pin=SecureString.from_env("FINTS_PIN"),
        )
