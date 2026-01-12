"""Currency value object for representing monetary currencies."""

from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

# ISO 4217 currecny codes. Currently only EUR is supported
SUPPORTED_CURRENCIES: set[str] = {
    "EUR",
    "USD",
    "GBP",
    "CHF",
    "JPY",
    "CAD",
    "AUD",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "CZK",
    "HUF",
    "BGN",
    "RON",
    "HRK",
    "RUB",
    "CNY",
    "INR",
    "BRL",
}

DEFAULT_CURRENCY = "EUR"


class Currency(BaseModel):
    """Value object representing a monetary currency."""

    code: str

    model_config = ConfigDict(
        frozen=True,  # Immutable
        str_strip_whitespace=True,  # Auto-strip whitespace
    )

    # overriding pydantic init to allow positional arguments Currency("EUR")
    def __init__(self, code: str | None = None, **data: Any):
        if "code" not in data:
            data["code"] = code
        super().__init__(**data)

    @field_validator("code")
    @classmethod
    def validate_and_normalize_code(cls, v: Any) -> str:
        if not v or len(str(v).strip()) == 0:
            msg = "Currency code cannot be empty"
            raise ValueError(msg)

        # Normalize to uppercase
        normalized_code = str(v).upper().strip()

        # Validate currency code format
        if len(normalized_code) != 3:
            msg = f"Currency code must be 3 characters long: {normalized_code}"
            raise ValueError(msg)

        if not normalized_code.isalpha():
            msg = f"Currency code must contain only letters: {normalized_code}"
            raise ValueError(msg)

        # Optional: Validate against supported currencies
        if normalized_code not in SUPPORTED_CURRENCIES:
            supported = sorted(SUPPORTED_CURRENCIES)
            msg = (
                f"Unsupported currency code: {normalized_code}. Supported: {supported}"
            )
            raise ValueError(msg)

        return normalized_code

    @classmethod
    def default(cls) -> "Currency":
        return cls(DEFAULT_CURRENCY)

    @classmethod
    def from_string(cls, currency_str: str) -> "Currency":
        return cls(currency_str)

    def __str__(self) -> str:
        return self.code

    def __eq__(self, other) -> bool:
        if isinstance(other, Currency):
            return self.code == other.code
        if isinstance(other, str):
            return self.code == other.upper()
        return False

    def __hash__(self) -> int:
        return hash(self.code)
