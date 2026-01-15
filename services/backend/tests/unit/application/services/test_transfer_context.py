"""Unit tests for TransferContext dataclass."""

from datetime import date
from uuid import uuid4

import pytest

from swen.application.services.transfer_reconciliation_service import TransferContext
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency

TEST_USER_ID = uuid4()


class TestTransferContextIsPreOpeningBalance:
    """Tests for TransferContext.is_pre_opening_balance method."""

    @pytest.fixture
    def asset_account(self) -> Account:
        """Create a sample asset account."""
        return Account(
            name="Test Account",
            account_type=AccountType.ASSET,
            account_number="1000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

    def test_returns_true_when_transaction_before_opening_balance(
        self,
        asset_account: Account,
    ):
        """Should return True when transaction date is before OB date."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=asset_account,
            counterparty_opening_balance_date=date(2025, 1, 20),
        )

        # Transaction on 2025-01-15, OB on 2025-01-20
        assert context.is_pre_opening_balance(date(2025, 1, 15)) is True

    def test_returns_false_when_transaction_on_opening_balance_date(
        self,
        asset_account: Account,
    ):
        """Should return False when transaction date equals OB date."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=asset_account,
            counterparty_opening_balance_date=date(2025, 1, 20),
        )

        # Transaction on same day as OB
        assert context.is_pre_opening_balance(date(2025, 1, 20)) is False

    def test_returns_false_when_transaction_after_opening_balance(
        self,
        asset_account: Account,
    ):
        """Should return False when transaction date is after OB date."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=asset_account,
            counterparty_opening_balance_date=date(2025, 1, 20),
        )

        # Transaction after OB
        assert context.is_pre_opening_balance(date(2025, 2, 1)) is False

    def test_returns_false_when_no_opening_balance_date(
        self,
        asset_account: Account,
    ):
        """Should return False when counterparty has no opening balance."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=asset_account,
            counterparty_opening_balance_date=None,  # No OB
        )

        assert context.is_pre_opening_balance(date(2025, 1, 15)) is False

    def test_returns_false_for_external_counterparty(self):
        """Should return False when there's no counterparty account."""
        context = TransferContext.external_counterparty("DE89370400440532013000")

        assert context.is_pre_opening_balance(date(2025, 1, 15)) is False

    def test_returns_false_for_not_a_transfer(self):
        """Should return False when there's no transfer context."""
        context = TransferContext.not_a_transfer()

        assert context.is_pre_opening_balance(date(2025, 1, 15)) is False


class TestTransferContextProperties:
    """Tests for TransferContext properties."""

    @pytest.fixture
    def asset_account(self) -> Account:
        """Create a sample asset account."""
        return Account(
            name="Test Asset",
            account_type=AccountType.ASSET,
            account_number="1000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

    @pytest.fixture
    def liability_account(self) -> Account:
        """Create a sample liability account."""
        return Account(
            name="Credit Card",
            account_type=AccountType.LIABILITY,
            account_number="2000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )

    def test_is_internal_transfer_true_with_counterparty_account(
        self,
        asset_account: Account,
    ):
        """Should be internal transfer when counterparty account exists."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=asset_account,
        )

        assert context.is_internal_transfer is True

    def test_is_internal_transfer_false_without_counterparty_account(self):
        """Should not be internal transfer when no counterparty account."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=None,
        )

        assert context.is_internal_transfer is False

    def test_is_asset_transfer_true_for_asset_counterparty(
        self,
        asset_account: Account,
    ):
        """Should be asset transfer when counterparty is asset account."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=asset_account,
        )

        assert context.is_asset_transfer is True

    def test_is_asset_transfer_false_for_liability_counterparty(
        self,
        liability_account: Account,
    ):
        """Should not be asset transfer when counterparty is liability."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=liability_account,
        )

        assert context.is_asset_transfer is False

    def test_is_liability_transfer_true_for_liability_counterparty(
        self,
        liability_account: Account,
    ):
        """Should be liability transfer when counterparty is liability."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=liability_account,
        )

        assert context.is_liability_transfer is True

    def test_can_reconcile_true_for_asset_transfer_with_iban(
        self,
        asset_account: Account,
    ):
        """Should be able to reconcile asset transfers with IBAN."""
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=asset_account,
        )

        assert context.can_reconcile is True

    def test_can_reconcile_false_without_iban(
        self,
        asset_account: Account,
    ):
        """Should not be able to reconcile without IBAN."""
        context = TransferContext(
            counterparty_iban=None,
            counterparty_account=asset_account,
        )

        assert context.can_reconcile is False


class TestTransferContextFactoryMethods:
    """Tests for TransferContext factory methods."""

    def test_not_a_transfer_returns_empty_context(self):
        """Should return context with no counterparty info."""
        context = TransferContext.not_a_transfer()

        assert context.counterparty_iban is None
        assert context.counterparty_account is None
        assert context.counterparty_opening_balance_date is None
        assert context.is_internal_transfer is False

    def test_external_counterparty_returns_iban_only(self):
        """Should return context with IBAN but no account."""
        iban = "DE89370400440532013000"
        context = TransferContext.external_counterparty(iban)

        assert context.counterparty_iban == iban
        assert context.counterparty_account is None
        assert context.counterparty_opening_balance_date is None
        assert context.is_internal_transfer is False
