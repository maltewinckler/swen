"""Unit tests for Geldstrom Adapter Anti-Corruption Layer mappings.

These tests verify that the adapter correctly translates geldstrom-specific
data structures to our domain model, protecting the domain from external changes.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

# Import geldstrom domain models for creating test fixtures
from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BankRoute,
    TransactionEntry,
)

from swen.domain.banking.value_objects.bank_account import BankAccount
from swen.domain.banking.value_objects.bank_transaction import BankTransaction
from swen.infrastructure.banking.geldstrom_adapter import GeldstromAdapter

# ═══════════════════════════════════════════════════════════════
#                     Fixtures for Mock Data
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def adapter():
    """Create GeldstromAdapter instance for testing."""
    return GeldstromAdapter()


@pytest.fixture
def mock_geldstrom_account():
    """Create geldstrom Account object."""
    return Account(
        account_id="532013000:00",
        iban="DE89370400440532013000",
        bic="COBADEFFXXX",
        currency="EUR",
        product_name="Girokonto",
        owner=AccountOwner(name="Max Mustermann"),
        bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        capabilities=AccountCapabilities(
            can_fetch_balance=True,
            can_list_transactions=True,
        ),
    )


@pytest.fixture
def mock_geldstrom_transaction():
    """Create geldstrom TransactionEntry object."""
    return TransactionEntry(
        entry_id="TX123456",
        booking_date=date(2025, 10, 20),
        value_date=date(2025, 10, 20),
        amount=Decimal("100.50"),
        currency="EUR",
        purpose="Test transaction",
        counterpart_name="John Doe",
        counterpart_iban="DE89370400440532013001",
        metadata={
            "bic": "COBADEFFXXX",
            "customer_reference": "REF789",
            "end_to_end_reference": "E2E-REF-001",
            "transaction_code": "005",
            "posting_text": "SEPA Transfer",
        },
    )


# ═══════════════════════════════════════════════════════════════
#                  Account Mapping Tests
# ═══════════════════════════════════════════════════════════════


class TestAccountMapping:
    """Test _map_account_to_domain() Anti-Corruption Layer."""

    def test_map_complete_account(self, adapter, mock_geldstrom_account):
        """Should map complete geldstrom account to domain model."""
        result = adapter._map_account_to_domain(
            mock_geldstrom_account,
            balance=Decimal("100.00"),
            balance_date=datetime(2025, 10, 20, tzinfo=timezone.utc),
        )

        assert isinstance(result, BankAccount)
        assert result.iban == "DE89370400440532013000"
        assert result.account_number == "532013000"
        assert result.blz == "37040044"
        assert result.account_holder == "Max Mustermann"
        assert result.bic == "COBADEFFXXX"
        assert result.account_type == "Girokonto"
        assert result.currency == "EUR"
        assert result.balance == Decimal("100.00")

    def test_map_account_extracts_account_number_from_id(
        self,
        adapter,
        mock_geldstrom_account,
    ):
        """Should extract account number from account_id."""
        result = adapter._map_account_to_domain(mock_geldstrom_account)

        # account_id is "532013000:00", should extract "532013000"
        assert result.account_number == "532013000"

    def test_map_account_with_missing_owner(self, adapter):
        """Should handle missing owner gracefully."""
        account = Account(
            account_id="532013000:00",
            iban="DE89370400440532013000",
            owner=None,  # No owner
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )

        result = adapter._map_account_to_domain(account)

        assert result.account_holder == "Unknown"

    def test_map_account_with_missing_product_name(self, adapter):
        """Should handle missing product name."""
        account = Account(
            account_id="532013000:00",
            iban="DE89370400440532013000",
            product_name=None,  # No product name
            owner=AccountOwner(name="Max Mustermann"),
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )

        result = adapter._map_account_to_domain(account)

        assert result.account_type == "Unknown Account Type"

    def test_map_account_with_missing_currency(self, adapter):
        """Should default to EUR when currency missing."""
        account = Account(
            account_id="532013000:00",
            iban="DE89370400440532013000",
            currency=None,  # No currency
            owner=AccountOwner(name="Max Mustermann"),
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )

        result = adapter._map_account_to_domain(account)

        assert result.currency == "EUR"

    def test_map_account_with_missing_bic(self, adapter):
        """Should handle missing BIC (optional field)."""
        account = Account(
            account_id="532013000:00",
            iban="DE89370400440532013000",
            bic=None,  # No BIC
            owner=AccountOwner(name="Max Mustermann"),
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )

        result = adapter._map_account_to_domain(account)

        assert result.bic is None

    def test_map_account_with_invalid_bic_length(self, adapter):
        """Should handle invalid BIC length."""
        account = Account(
            account_id="532013000:00",
            iban="DE89370400440532013000",
            bic="THIISBICTOOLONG",  # Invalid length > 11
            owner=AccountOwner(name="Max Mustermann"),
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )

        result = adapter._map_account_to_domain(account)

        assert result.bic is None  # Should be set to None

    def test_map_account_without_balance(self, adapter, mock_geldstrom_account):
        """Should handle account without balance."""
        result = adapter._map_account_to_domain(mock_geldstrom_account)

        assert result.balance is None
        assert result.balance_date is None


# ═══════════════════════════════════════════════════════════════
#                Transaction Mapping Tests
# ═══════════════════════════════════════════════════════════════


class TestTransactionMapping:
    """Test _map_transaction_to_domain() Anti-Corruption Layer."""

    def test_map_complete_transaction(self, adapter, mock_geldstrom_transaction):
        """Should map complete geldstrom transaction to domain model."""
        result = adapter._map_transaction_to_domain(mock_geldstrom_transaction)

        assert isinstance(result, BankTransaction)
        assert result.booking_date == date(2025, 10, 20)
        assert result.value_date == date(2025, 10, 20)
        assert result.amount == Decimal("100.50")
        assert result.currency == "EUR"
        assert result.purpose == "Test transaction"
        assert result.applicant_name == "John Doe"
        assert result.applicant_iban == "DE89370400440532013001"
        assert result.applicant_bic == "COBADEFFXXX"
        assert result.bank_reference == "TX123456"
        assert result.customer_reference == "REF789"
        assert result.end_to_end_reference == "E2E-REF-001"
        assert result.transaction_code == "005"
        assert result.posting_text == "SEPA Transfer"

    def test_map_transaction_with_minimal_metadata(self, adapter):
        """Should handle transaction with minimal metadata."""
        entry = TransactionEntry(
            entry_id="TX999",
            booking_date=date(2025, 10, 20),
            value_date=date(2025, 10, 20),
            amount=Decimal("50.00"),
            currency="EUR",
            purpose="Simple transfer",
            metadata={},  # No extra metadata
        )

        result = adapter._map_transaction_to_domain(entry)

        assert result.applicant_name is None
        assert result.applicant_iban is None
        assert result.applicant_bic is None
        assert result.customer_reference is None
        assert result.bank_reference == "TX999"

    def test_map_negative_amount_debit(self, adapter):
        """Should correctly handle negative amounts (debit)."""
        entry = TransactionEntry(
            entry_id="TX001",
            booking_date=date(2025, 10, 20),
            value_date=date(2025, 10, 20),
            amount=Decimal("-50.75"),
            currency="EUR",
            purpose="Payment",
        )

        result = adapter._map_transaction_to_domain(entry)

        assert result.amount == Decimal("-50.75")
        assert result.is_debit()
        assert not result.is_credit()

    def test_map_positive_amount_credit(self, adapter):
        """Should correctly handle positive amounts (credit)."""
        entry = TransactionEntry(
            entry_id="TX001",
            booking_date=date(2025, 10, 20),
            value_date=date(2025, 10, 20),
            amount=Decimal("100.00"),
            currency="EUR",
            purpose="Salary",
        )

        result = adapter._map_transaction_to_domain(entry)

        assert result.amount == Decimal("100.00")
        assert result.is_credit()
        assert not result.is_debit()

    def test_map_transaction_with_empty_purpose(self, adapter):
        """Should handle empty purpose with fallback."""
        entry = TransactionEntry(
            entry_id="TX001",
            booking_date=date(2025, 10, 20),
            value_date=date(2025, 10, 20),
            amount=Decimal("10.00"),
            currency="EUR",
            purpose="",  # Empty purpose
        )

        result = adapter._map_transaction_to_domain(entry)

        assert result.purpose == "No description"

    def test_map_transactions_list(self, adapter, mock_geldstrom_transaction):
        """Should map a list of transactions."""
        entries = [mock_geldstrom_transaction, mock_geldstrom_transaction]

        result = adapter._map_transactions_to_domain(entries)

        assert len(result) == 2
        assert all(isinstance(tx, BankTransaction) for tx in result)


# ═══════════════════════════════════════════════════════════════
#                    Edge Cases and Robustness
# ═══════════════════════════════════════════════════════════════


class TestACLRobustness:
    """Test ACL handles edge cases and malformed data."""

    def test_account_mapping_with_minimal_data(self, adapter):
        """Should handle account with only required fields."""
        minimal_account = Account(
            account_id="123456:00",
            iban="DE89370400440532013000",
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )

        result = adapter._map_account_to_domain(minimal_account)

        assert result.iban == "DE89370400440532013000"
        assert result.account_number == "123456"
        assert result.blz == "37040044"
        assert result.account_holder == "Unknown"
        assert result.account_type == "Unknown Account Type"
        assert result.currency == "EUR"

    def test_transaction_with_zero_amount(self, adapter):
        """Should handle transactions with zero amount."""
        entry = TransactionEntry(
            entry_id="TX001",
            booking_date=date(2025, 10, 20),
            value_date=date(2025, 10, 20),
            amount=Decimal("0.00"),
            currency="EUR",
            purpose="Zero transaction",
        )

        result = adapter._map_transaction_to_domain(entry)

        assert result.amount == Decimal("0.00")
        assert not result.is_credit()
        assert not result.is_debit()

    def test_account_without_iban_raises_error(self, adapter):
        """Should raise validation error for account without IBAN.

        Accounts from geldstrom should always have a valid IBAN.
        If not, the domain BankAccount validation will fail.
        """
        account = Account(
            account_id="123456:00",
            iban=None,  # No IBAN
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )

        # Missing IBAN should cause validation error in BankAccount
        with pytest.raises(Exception):  # ValidationError from Pydantic
            adapter._map_account_to_domain(account)

    def test_find_geldstrom_account_by_iban(self, adapter, mock_geldstrom_account):
        """Should find account by IBAN."""
        adapter._geldstrom_accounts_cache = [mock_geldstrom_account]

        result = adapter._find_geldstrom_account("DE89370400440532013000")

        assert result is not None
        assert result.iban == "DE89370400440532013000"

    def test_find_geldstrom_account_not_found(self, adapter, mock_geldstrom_account):
        """Should return None when account not found."""
        adapter._geldstrom_accounts_cache = [mock_geldstrom_account]

        result = adapter._find_geldstrom_account("DE00000000000000000000")

        assert result is None

    def test_find_geldstrom_account_empty_cache(self, adapter):
        """Should return None when cache is empty."""
        adapter._geldstrom_accounts_cache = None

        result = adapter._find_geldstrom_account("DE89370400440532013000")

        assert result is None


# ═══════════════════════════════════════════════════════════════
#                    Date/Datetime Conversion Tests
# ═══════════════════════════════════════════════════════════════


class TestDatetimeToDateConversion:
    """Test that datetime objects are correctly converted to date objects.

    The geldstrom library strictly requires date objects (not datetime).
    The adapter should handle this conversion transparently.
    """

    @pytest.mark.asyncio
    async def test_fetch_transactions_converts_datetime_to_date(self, adapter):
        """Should convert datetime start_date to date before calling geldstrom."""

        # Setup mock client
        mock_client = Mock()
        mock_client.get_transactions = Mock(return_value=Mock(entries=[]))
        adapter._client = mock_client

        # Setup mock account
        mock_account = Account(
            account_id="123456:00",
            iban="DE89370400440532013000",
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )
        adapter._geldstrom_accounts_cache = [mock_account]

        # Pass datetime objects (as the sync command does)
        start_datetime = datetime(2025, 9, 3, 10, 30, 0, tzinfo=timezone.utc)
        end_datetime = datetime(2025, 12, 2, 15, 45, 30, tzinfo=timezone.utc)

        await adapter.fetch_transactions(
            account_iban="DE89370400440532013000",
            start_date=start_datetime,
            end_date=end_datetime,
        )

        # Verify geldstrom was called with date objects, not datetime
        call_kwargs = mock_client.get_transactions.call_args.kwargs
        assert isinstance(call_kwargs["start_date"], date)
        assert not isinstance(call_kwargs["start_date"], datetime)
        assert isinstance(call_kwargs["end_date"], date)
        assert not isinstance(call_kwargs["end_date"], datetime)

        # Verify the date values are correct
        assert call_kwargs["start_date"] == date(2025, 9, 3)
        assert call_kwargs["end_date"] == date(2025, 12, 2)

    @pytest.mark.asyncio
    async def test_fetch_transactions_accepts_date_objects(self, adapter):
        """Should work correctly with date objects (no conversion needed)."""

        # Setup mock client
        mock_client = Mock()
        mock_client.get_transactions = Mock(return_value=Mock(entries=[]))
        adapter._client = mock_client

        # Setup mock account
        mock_account = Account(
            account_id="123456:00",
            iban="DE89370400440532013000",
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )
        adapter._geldstrom_accounts_cache = [mock_account]

        # Pass date objects directly
        start_date = date(2025, 9, 3)
        end_date = date(2025, 12, 2)

        await adapter.fetch_transactions(
            account_iban="DE89370400440532013000",
            start_date=start_date,
            end_date=end_date,
        )

        # Verify geldstrom was called with the same date objects
        call_kwargs = mock_client.get_transactions.call_args.kwargs
        assert call_kwargs["start_date"] == date(2025, 9, 3)
        assert call_kwargs["end_date"] == date(2025, 12, 2)

    @pytest.mark.asyncio
    async def test_fetch_transactions_with_none_end_date(self, adapter):
        """Should default end_date to today (UTC) when None is passed."""
        from datetime import timezone

        # Setup mock client
        mock_client = Mock()
        mock_client.get_transactions = Mock(return_value=Mock(entries=[]))
        adapter._client = mock_client

        # Setup mock account
        mock_account = Account(
            account_id="123456:00",
            iban="DE89370400440532013000",
            bank_route=BankRoute(country_code="DE", bank_code="37040044"),
        )
        adapter._geldstrom_accounts_cache = [mock_account]

        # Pass only start_date, end_date defaults to None -> today (UTC)
        start_date = date(2025, 9, 3)

        await adapter.fetch_transactions(
            account_iban="DE89370400440532013000",
            start_date=start_date,
            end_date=None,
        )

        # Verify end_date was set to today (UTC-based, matching adapter implementation)
        call_kwargs = mock_client.get_transactions.call_args.kwargs
        expected_today = datetime.now(tz=timezone.utc).date()
        assert call_kwargs["end_date"] == expected_today
