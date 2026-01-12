"""Bank transaction value object."""

import hashlib
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from swen.domain.shared.iban import normalize_iban


def _sha256_hash(value: str) -> str:
    """Compute SHA-256 hash of a string, returning hex digest."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class BankTransaction(BaseModel):
    """Value object representing a bank transaction coming from the bank."""

    booking_date: date = Field(..., description="When transaction was booked")
    value_date: date = Field(..., description="When money actually moved")
    amount: Decimal = Field(..., description="Transaction amount")
    currency: str = Field(..., max_length=3, description="only EUR supported")
    purpose: str = Field(..., min_length=1, description="Transaction description")

    applicant_name: str | None = Field(
        default=None,
        max_length=255,
        description="Name of counterparty",
    )
    applicant_iban: str | None = Field(
        default=None,
        max_length=34,
        description="IBAN of counterparty",
    )
    applicant_bic: str | None = Field(
        default=None,
        max_length=11,
        description="BIC of counterparty bank",
    )

    bank_reference: str | None = Field(default=None, max_length=255)
    customer_reference: str | None = Field(default=None, max_length=255)
    end_to_end_reference: str | None = Field(default=None, max_length=255)
    mandate_reference: str | None = Field(default=None, max_length=255)
    creditor_id: str | None = Field(default=None, max_length=255)

    transaction_code: str | None = Field(default=None, max_length=10)
    posting_text: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(
        frozen=True,  # Immutable
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_serializer("amount")
    def serialize_amount(self, value: Decimal) -> str:
        return str(value)

    @field_serializer("booking_date", "value_date")
    def serialize_date(self, value: date) -> str:
        return value.isoformat()

    def is_credit(self) -> bool:
        return self.amount > 0

    def is_debit(self) -> bool:
        return self.amount < 0

    def compute_identity_hash(self, account_identifier: int | str) -> str:
        """Compute a stable identity hash for this transaction."""

        def normalize(value: str | None) -> str:
            return (value or "").strip()

        identity_string = (
            f"{account_identifier}|"
            f"{self.booking_date.isoformat()}|"
            f"{self.amount}|"
            f"{normalize(self.end_to_end_reference)}|"
            f"{normalize_iban(self.applicant_iban) or ''}|"
            f"{normalize(self.purpose)[:50]}"
        )
        return _sha256_hash(identity_string)

    @staticmethod
    def compute_transfer_hash(
        iban_a: str,
        iban_b: str,
        booking_date: date,
        amount: Decimal,
    ) -> str:
        """Compute a SHA-256 hash for internal transfers."""
        # Normalize and sort IBANs alphabetically so order doesn't matter
        norm_a = normalize_iban(iban_a) or ""
        norm_b = normalize_iban(iban_b) or ""
        sorted_ibans = sorted([norm_a, norm_b])

        # Normalize amount to 2 decimal places for consistent hashing
        # (banks may return 700 or 700.00 for the same amount)
        normalized_amount = f"{abs(amount):.2f}"

        identity_string = (
            f"TRANSFER|{sorted_ibans[0]}|{sorted_ibans[1]}|"
            f"{booking_date.isoformat()}|"
            f"{normalized_amount}"
        )
        return _sha256_hash(identity_string)

    def compute_transfer_identity_hash(
        self,
        source_iban: str,
        destination_iban: str,
    ) -> str:
        return BankTransaction.compute_transfer_hash(
            iban_a=source_iban,
            iban_b=destination_iban,
            booking_date=self.booking_date,
            amount=self.amount,
        )

    def __str__(self) -> str:
        direction = "+" if self.is_credit() else ""
        return (
            f"{self.booking_date}: {direction}{self.amount} {self.currency} "
            f"- {self.purpose[:50]}"
        )
