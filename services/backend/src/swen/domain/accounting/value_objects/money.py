"""Value objects for monetary amounts and financial identifiers."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from swen.domain.accounting.value_objects.currency import Currency

# Constants for validation
DECIMAL_PLACES_LIMIT = -2


class Money(BaseModel):
    """Value object representing monetary amounts with currency."""

    amount: Decimal
    currency: Currency = Currency.default()

    model_config = ConfigDict(
        frozen=True,  # Immutable
        arbitrary_types_allowed=False,  # Currency is now Pydantic-native
    )

    def __init__(
        self,
        amount: Decimal | float | str | None = None,
        currency: Currency | str | None = None,
        **data: Any,
    ):
        # If currency is None and not provided in data, use default
        if currency is None and "currency" not in data:
            currency = Currency.default()
        super().__init__(amount=amount, currency=currency, **data)

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> Decimal:
        if not isinstance(v, Decimal):
            v = Decimal(str(v))

        decimal_places = v.as_tuple().exponent
        if not isinstance(decimal_places, int):
            msg = "Money amount must have a valid decimal exponent"
            raise ValueError(msg)

        if decimal_places < DECIMAL_PLACES_LIMIT:
            msg = "Money cannot have more than 2 decimal places"
            raise ValueError(msg)

        return v

    @field_validator("currency", mode="before")
    @classmethod
    def validate_currency(cls, v: Any) -> Currency:
        if isinstance(v, Currency):
            return v
        if isinstance(v, str):
            return Currency(v)
        msg = f"Currency must be Currency instance or string, got {type(v)}"
        raise TypeError(msg)

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            msg = f"Cannot add different currencies: {self.currency} + {other.currency}"
            raise ValueError(msg)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if self.currency != other.currency:
            msg = f"Cannot subtract different currencies: {self.currency} - {other.currency}"  # NOQA: E501
            raise ValueError(msg)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | float) -> Money:
        if not isinstance(factor, (Decimal, int, float)):
            msg = "Money can only be multiplied by numeric values"
            raise ValueError(msg)
        new_amount = (self.amount * Decimal(str(factor))).quantize(Decimal("0.01"))
        return Money(new_amount, self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: Money) -> bool:
        if self.currency != other.currency:
            msg = f"Cannot compare different currencies: {self.currency} < {other.currency}"  # NOQA: E501
            raise ValueError(msg)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        if self.currency != other.currency:
            msg = f"Cannot compare different currencies: {self.currency} <= {other.currency}"  # NOQA: E501
            raise ValueError(msg)
        return self.amount <= other.amount

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"

    def is_zero(self) -> bool:
        return self.amount == Decimal(0)

    def is_positive(self) -> bool:
        return self.amount > Decimal(0)

    def is_negative(self) -> bool:
        return self.amount < Decimal(0)

    def abs(self) -> Money:
        return Money(abs(self.amount), self.currency)
