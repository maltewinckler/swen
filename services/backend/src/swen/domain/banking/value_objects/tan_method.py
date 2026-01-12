"""TAN Method value object.

Represents an available TAN authentication method supported by a bank.
This is used during credential setup to discover which methods are available.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class TANMethodType(str, Enum):
    """Type of TAN authentication method."""

    DECOUPLED = "decoupled"
    PUSH = "push"
    SMS = "sms"
    CHIPTAN = "chiptan"
    PHOTO_TAN = "photo_tan"
    MANUAL = "manual"
    UNKNOWN = "unknown"


class TANMethod(BaseModel):
    """Represents a TAN authentication method supported by a bank."""

    # TODO: THIS MIGHT BE DEPENDENT ON THE FINTS PROTOCOL, ADDING ADDITIONAL ABSTRACTION
    # SEEMS NOT REASONABLE AT THIS POINT.
    code: str = Field(..., description="Tan ID code (e.g., '946', '972')")
    name: str = Field(..., description="e.g., 'SecureGo plus'")
    method_type: TANMethodType = Field(default=TANMethodType.UNKNOWN)
    is_decoupled: bool = Field(default=False, description="True if app-based approval")

    # Technical identifiers -> FINTS Specific??
    technical_id: str | None = Field(default=None)
    zka_id: str | None = Field(default=None)
    zka_version: str | None = Field(default=None)

    max_tan_length: int | None = Field(default=None)

    # Decoupled method timing configuration
    decoupled_max_polls: int | None = Field(default=None)
    decoupled_first_poll_delay: int | None = Field(default=None)
    decoupled_poll_interval: int | None = Field(default=None)

    # Capabilities
    supports_cancel: bool = Field(default=False)
    supports_multiple_tan: bool = Field(default=False)

    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
    )

    def __str__(self) -> str:
        type_str = " (app-based)" if self.is_decoupled else ""
        return f"{self.code}: {self.name}{type_str}"

    @property
    def is_interactive(self) -> bool:
        return not self.is_decoupled
