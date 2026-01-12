"""Bank account value object."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class BankAccount(BaseModel):
    """
    Value object representing a bank account.

    This is the domain's view of a bank account as returned
    from external banking systems (FinTS, PSD2, etc.).
    """

    # Core identification
    iban: str = Field(
        ...,
        min_length=15,
        max_length=34,
        description="International Bank Account Number",
    )
    account_number: str = Field(..., max_length=50, description="Local account number")
    blz: str = Field(
        ...,
        min_length=8,
        max_length=8,
        description="Bankleitzahl (German bank code)",
    )

    # Account holder information
    account_holder: str = Field(
        ...,
        max_length=255,
        description="Name of account holder",
    )
    account_type: str = Field(
        ...,
        max_length=50,
        description="Type of account (e.g., 'Girokonto', 'Sparkonto')",
    )

    # Optional fields with defaults
    currency: str = Field(
        default="EUR",
        max_length=3,
        description="Account currency code",
    )
    bic: str | None = Field(
        default=None,
        max_length=11,
        description="Bank Identifier Code (SWIFT/BIC)",
    )
    bank_name: str | None = Field(
        default=None,
        max_length=255,
        description="Name of the bank",
    )

    # Balance information (added for database compatibility)
    balance: Decimal | None = Field(
        default=None,
        description="Current balance (if available)",
    )
    balance_date: datetime | None = Field(
        default=None,
        description="Timestamp when balance was fetched",
    )

    model_config = ConfigDict(
        frozen=True,  # Immutable like dataclass(frozen=True)
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_serializer("balance")
    def serialize_balance(self, value: Decimal | None) -> str | None:
        return str(value) if value is not None else None

    @field_validator("blz")
    @classmethod
    def validate_blz(cls, v: str) -> str:
        if not v.isdigit():
            msg = "BLZ must contain only digits"
            raise ValueError(msg)
        return v

    @field_validator("iban")
    @classmethod
    def validate_iban(cls, v: str) -> str:
        # Remove spaces for flexibility
        v = v.replace(" ", "").upper()
        if not v[:2].isalpha() or not v[2:4].isdigit():
            msg = "IBAN must start with 2 letters followed by 2 digits"
            raise ValueError(msg)
        return v

    def __str__(self) -> str:
        balance_str = f" ({self.balance} {self.currency})" if self.balance else ""
        return f"{self.account_holder} - {self.iban}{balance_str}"
