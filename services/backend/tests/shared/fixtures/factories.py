"""
Test data factories for creating deterministic test entities.

These factories provide consistent test data across all tests.
Use fixed UUIDs and predictable values to ensure reproducibility.

Usage:
    from tests.shared.fixtures.factories import TestUserFactory, TestAccountFactory

    def test_something():
        user = TestUserFactory.alice()
        account = TestAccountFactory.checking_account()
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from swen.application.ports.identity import CurrentUser


@dataclass(frozen=True)
class TestUserFactory:
    """Factory for creating test users with deterministic IDs.

    Use these fixed users throughout tests for consistency.
    The UUIDs are designed to be easily recognizable in logs and debugging.
    """

    # Primary test user (default for most tests)
    DEFAULT_ID = UUID("12345678-1234-5678-1234-567812345678")
    DEFAULT_EMAIL = "test@example.com"

    # Named test users for multi-user scenarios
    ALICE_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    ALICE_EMAIL = "alice@example.com"

    BOB_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    BOB_EMAIL = "bob@example.com"

    # Admin user
    ADMIN_ID = UUID("00000000-0000-0000-0000-000000000001")
    ADMIN_EMAIL = "admin@example.com"

    # Secondary user for isolation tests
    SECONDARY_ID = UUID("00000000-0000-0000-0000-000000000002")
    SECONDARY_EMAIL = "test2@example.com"

    @classmethod
    def default(cls) -> dict:
        """Default test user."""
        return {"id": cls.DEFAULT_ID, "email": cls.DEFAULT_EMAIL}

    @classmethod
    def default_current_user(cls) -> CurrentUser:
        """Default test user as CurrentUser."""
        return CurrentUser(user_id=cls.DEFAULT_ID, email=cls.DEFAULT_EMAIL)

    @classmethod
    def alice(cls) -> dict:
        """Alice - first named test user."""
        return {"id": cls.ALICE_ID, "email": cls.ALICE_EMAIL}

    @classmethod
    def alice_current_user(cls) -> CurrentUser:
        """Alice as CurrentUser."""
        return CurrentUser(user_id=cls.ALICE_ID, email=cls.ALICE_EMAIL)

    @classmethod
    def bob(cls) -> dict:
        """Bob - second named test user."""
        return {"id": cls.BOB_ID, "email": cls.BOB_EMAIL}

    @classmethod
    def bob_current_user(cls) -> CurrentUser:
        """Bob as CurrentUser."""
        return CurrentUser(user_id=cls.BOB_ID, email=cls.BOB_EMAIL)

    @classmethod
    def admin(cls) -> dict:
        """Admin test user."""
        return {"id": cls.ADMIN_ID, "email": cls.ADMIN_EMAIL}

    @classmethod
    def secondary(cls) -> dict:
        """Secondary test user for isolation tests."""
        return {"id": cls.SECONDARY_ID, "email": cls.SECONDARY_EMAIL}


@dataclass(frozen=True)
class TestAccountFactory:
    """Factory for creating test bank accounts.

    Provides realistic German bank account data for testing.
    """

    # Standard test IBANs (valid format, not real accounts)
    CHECKING_IBAN = "DE89370400440532013000"
    SAVINGS_IBAN = "DE89370400440532013001"
    SECOND_BANK_IBAN = "DE12500000001234567890"

    @classmethod
    def checking_account(cls, **overrides) -> dict:
        """Standard checking account."""
        defaults = {
            "iban": cls.CHECKING_IBAN,
            "account_number": "532013000",
            "blz": "37040044",
            "account_holder": "Max Mustermann",
            "account_type": "Girokonto",
            "currency": "EUR",
            "bic": "COBADEFFXXX",
            "bank_name": "Commerzbank",
            "balance": Decimal("1234.56"),
            "balance_date": datetime(2025, 10, 30, 12, 0, 0, tzinfo=timezone.utc),
        }
        defaults.update(overrides)
        return defaults

    @classmethod
    def savings_account(cls, **overrides) -> dict:
        """Savings account."""
        defaults = {
            "iban": cls.SAVINGS_IBAN,
            "account_number": "532013001",
            "blz": "37040044",
            "account_holder": "Max Mustermann",
            "account_type": "Sparkonto",
            "currency": "EUR",
            "bic": "COBADEFFXXX",
            "bank_name": "Commerzbank",
            "balance": Decimal("5000.00"),
            "balance_date": datetime(2025, 10, 30, 12, 0, 0, tzinfo=timezone.utc),
        }
        defaults.update(overrides)
        return defaults


@dataclass(frozen=True)
class TestTransactionFactory:
    """Factory for creating test transactions.

    Provides realistic transaction data similar to FinTS responses.
    """

    @classmethod
    def expense(cls, **overrides) -> dict:
        """Standard expense transaction."""
        defaults = {
            "booking_date": date(2025, 10, 30),
            "value_date": date(2025, 10, 30),
            "amount": Decimal("-50.00"),
            "currency": "EUR",
            "purpose": "REWE Sagt Danke",
            "applicant_name": "REWE",
            "applicant_iban": "DE12345678901234567890",
            "bank_reference": "REF-001",
        }
        defaults.update(overrides)
        return defaults

    @classmethod
    def income(cls, **overrides) -> dict:
        """Income transaction (e.g., salary)."""
        defaults = {
            "booking_date": date(2025, 10, 28),
            "value_date": date(2025, 10, 28),
            "amount": Decimal("2500.00"),
            "currency": "EUR",
            "purpose": "Gehalt Oktober",
            "applicant_name": "Arbeitgeber GmbH",
            "applicant_iban": "DE98765432109876543210",
            "bank_reference": "REF-SALARY-001",
        }
        defaults.update(overrides)
        return defaults

    @classmethod
    def transfer(cls, **overrides) -> dict:
        """Internal transfer between accounts."""
        defaults = {
            "booking_date": date(2025, 10, 29),
            "value_date": date(2025, 10, 29),
            "amount": Decimal("-100.00"),
            "currency": "EUR",
            "purpose": "Umbuchung Sparkonto",
            "applicant_name": "Max Mustermann",
            "applicant_iban": TestAccountFactory.SAVINGS_IBAN,
            "bank_reference": "REF-TRANSFER-001",
        }
        defaults.update(overrides)
        return defaults

    @classmethod
    def batch(cls, count: int = 5, start_date: date | None = None) -> list[dict]:
        """Create a batch of transactions for testing.

        Args:
            count: Number of transactions to create.
            start_date: Starting date for transactions (defaults to 2025-10-01).

        Returns:
            List of transaction dictionaries.
        """
        from datetime import timedelta

        if start_date is None:
            start_date = date(2025, 10, 1)

        transactions = []
        for i in range(count):
            tx_date = start_date + timedelta(days=i)
            transactions.append(
                cls.expense(
                    booking_date=tx_date,
                    value_date=tx_date,
                    amount=Decimal(f"-{10 + i * 5}.00"),
                    purpose=f"Transaction {i + 1}",
                    bank_reference=f"REF-BATCH-{i + 1:03d}",
                ),
            )
        return transactions
