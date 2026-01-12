"""Unit tests for liability reconciliation in TransferReconciliationService."""

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from swen.application.services.transfer_reconciliation_service import (
    TransferContext,
    TransferReconciliationService,
)
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import (
    Currency,
    Money,
    TransactionMetadata,
    TransactionSource,
)

# Test user ID for all tests
TEST_USER_ID = uuid4()


class TestTransferContextAccountTypes:
    """Test TransferContext properties for distinguishing account types."""

    def test_is_asset_transfer_true_for_asset_counterparty(self):
        """Test is_asset_transfer returns True for ASSET counterparty."""
        asset_account = Account(
            name="External Bank",
            account_type=AccountType.ASSET,
            account_number="EXT-12345",
            user_id=TEST_USER_ID,
        )
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=asset_account,
        )

        assert context.is_asset_transfer is True
        assert context.is_liability_transfer is False
        assert context.is_internal_transfer is True
        assert context.can_reconcile is True

    def test_is_liability_transfer_true_for_liability_counterparty(self):
        """Test is_liability_transfer returns True for LIABILITY counterparty."""
        liability_account = Account(
            name="Credit Card",
            account_type=AccountType.LIABILITY,
            account_number="LIA-12345",
            user_id=TEST_USER_ID,
        )
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=liability_account,
        )

        assert context.is_liability_transfer is True
        assert context.is_asset_transfer is False
        assert context.is_internal_transfer is True
        # Liability transfers cannot be reconciled (one-sided)
        assert context.can_reconcile is False

    def test_can_reconcile_false_for_liability(self):
        """Test that liability transfers cannot be reconciled."""
        liability_account = Account(
            name="Student Loan",
            account_type=AccountType.LIABILITY,
            account_number="LIA-99999",
            user_id=TEST_USER_ID,
        )
        context = TransferContext(
            counterparty_iban="DE89370400440532013000",
            counterparty_account=liability_account,
        )

        # Liability transfers are one-sided, can't reconcile with "other leg"
        assert context.can_reconcile is False

    def test_external_counterparty_not_a_transfer(self):
        """Test external counterparty is not an internal/liability transfer."""
        context = TransferContext.external_counterparty("DE89370400440532013000")

        assert context.is_internal_transfer is False
        assert context.is_asset_transfer is False
        assert context.is_liability_transfer is False
        assert context.can_reconcile is False

    def test_not_a_transfer_has_all_flags_false(self):
        """Test not_a_transfer factory returns context with all flags False."""
        context = TransferContext.not_a_transfer()

        assert context.is_internal_transfer is False
        assert context.is_asset_transfer is False
        assert context.is_liability_transfer is False
        assert context.can_reconcile is False


class TestLiabilityReconciliation:
    """Test liability reconciliation in TransferReconciliationService."""

    def _make_service(self):
        """Create service with mocked repositories."""
        transaction_repo = AsyncMock()
        mapping_repo = AsyncMock()
        account_repo = AsyncMock()

        service = TransferReconciliationService(
            transaction_repository=transaction_repo,
            mapping_repository=mapping_repo,
            account_repository=account_repo,
        )

        return service, transaction_repo, mapping_repo, account_repo

    def _make_expense_transaction(
        self,
        amount: Decimal = Decimal("100.00"),
        counterparty_iban: str = "DE89370400440532013000",
    ):
        """Create a transaction with Expense and Asset entries (like from bank import)."""
        expense_account = Account(
            name="Sonstiges",
            account_type=AccountType.EXPENSE,
            account_number="4900",
            user_id=TEST_USER_ID,
        )
        bank_account = Account(
            name="Girokonto",
            account_type=AccountType.ASSET,
            account_number="1000",
            user_id=TEST_USER_ID,
            iban="DE51120700700756557355",
        )

        transaction = Transaction(
            description="Credit card payment",
            user_id=TEST_USER_ID,
        )
        money = Money(amount=amount, currency=Currency("EUR"))
        transaction.add_debit(expense_account, money)
        transaction.add_credit(bank_account, money)

        # Set first-class fields like a real bank import would
        # Note: source, counterparty_iban, source_iban, counterparty are now first-class fields
        transaction._source = TransactionSource.BANK_IMPORT
        transaction._source_iban = "DE51120700700756557355"
        transaction._counterparty_iban = counterparty_iban
        transaction._counterparty = "Credit Card Payment"

        return transaction, expense_account, bank_account

    @pytest.mark.asyncio
    async def test_reconcile_liability_for_new_account_converts_transactions(self):
        """Test that liability reconciliation converts expense transactions."""
        service, transaction_repo, mapping_repo, account_repo = self._make_service()

        # Create a liability account
        liability_account = Account(
            name="Norwegian VISA",
            account_type=AccountType.LIABILITY,
            account_number="LIA-12345",
            user_id=TEST_USER_ID,
            iban="DE89370400440532013000",
        )

        # Create an existing expense transaction to the credit card
        transaction, expense_account, bank_account = self._make_expense_transaction()

        # Mock: find transaction by counterparty IBAN (now a first-class field query)
        transaction_repo.find_by_counterparty_iban = AsyncMock(return_value=[transaction])
        transaction_repo.save = AsyncMock()

        # Act
        reconciled = await service.reconcile_liability_for_new_account(
            iban="DE89370400440532013000",
            liability_account=liability_account,
        )

        # Assert
        assert reconciled == 1
        transaction_repo.save.assert_called_once()

        # Transaction should now have liability as counter-account
        # and be marked as internal transfer with updated description
        saved_tx = transaction_repo.save.call_args[0][0]
        assert saved_tx.is_internal_transfer is True  # Now a first-class field
        assert saved_tx.description == "Payment to Norwegian VISA"
        assert saved_tx.counterparty == "Norwegian VISA"

    @pytest.mark.asyncio
    async def test_reconcile_liability_skips_already_reconciled(self):
        """Test that already reconciled transactions are skipped."""
        service, transaction_repo, mapping_repo, account_repo = self._make_service()

        liability_account = Account(
            name="Credit Card",
            account_type=AccountType.LIABILITY,
            account_number="LIA-12345",
            user_id=TEST_USER_ID,
        )

        # Create a transaction already marked as internal transfer
        transaction, _, _ = self._make_expense_transaction()
        # Mark as already reconciled (first-class field)
        transaction._is_internal_transfer = True

        transaction_repo.find_by_counterparty_iban = AsyncMock(return_value=[transaction])
        transaction_repo.save = AsyncMock()

        # Act
        reconciled = await service.reconcile_liability_for_new_account(
            iban="DE89370400440532013000",
            liability_account=liability_account,
        )

        # Assert - should skip already reconciled
        assert reconciled == 0
        transaction_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_reconcile_liability_handles_no_candidates(self):
        """Test that no error when no transactions match."""
        service, transaction_repo, mapping_repo, account_repo = self._make_service()

        liability_account = Account(
            name="Credit Card",
            account_type=AccountType.LIABILITY,
            account_number="LIA-12345",
            user_id=TEST_USER_ID,
        )

        # No transactions found
        transaction_repo.find_by_counterparty_iban = AsyncMock(return_value=[])

        # Act
        reconciled = await service.reconcile_liability_for_new_account(
            iban="DE89370400440532013000",
            liability_account=liability_account,
        )

        # Assert
        assert reconciled == 0

    @pytest.mark.asyncio
    async def test_bank_import_conversion_does_not_create_duplicate_entries(self):
        """Test that converting a bank import doesn't create duplicate asset entries.

        This is a regression test for a bug where clear_entries() preserved the
        asset entry for bank imports, but the conversion code then added another
        asset entry, resulting in unbalanced transactions.
        """
        service, transaction_repo, mapping_repo, account_repo = self._make_service()

        liability_account = Account(
            name="Credit Card",
            account_type=AccountType.LIABILITY,
            account_number="LIA-12345",
            user_id=TEST_USER_ID,
        )

        # Create a bank import transaction (has protected asset entry)
        transaction, _, _ = self._make_expense_transaction()

        # Verify it's a bank import with 2 entries
        assert transaction.is_bank_import is True
        assert len(transaction.entries) == 2

        transaction_repo.find_by_counterparty_iban = AsyncMock(return_value=[transaction])
        transaction_repo.save = AsyncMock()

        # Act
        reconciled = await service.reconcile_liability_for_new_account(
            iban="DE89370400440532013000",
            liability_account=liability_account,
        )

        # Assert
        assert reconciled == 1
        saved_tx = transaction_repo.save.call_args[0][0]

        # CRITICAL: Should still have exactly 2 entries (not 3!)
        assert len(saved_tx.entries) == 2, (
            f"Expected 2 entries but got {len(saved_tx.entries)}. "
            "This indicates duplicate entries were created."
        )

        # Verify entries are balanced
        total_debits = sum(e.debit.amount for e in saved_tx.entries)
        total_credits = sum(e.credit.amount for e in saved_tx.entries)
        assert total_debits == total_credits, (
            f"Transaction is unbalanced: debits={total_debits}, credits={total_credits}"
        )

    @pytest.mark.asyncio
    async def test_detect_transfer_returns_liability_context(self):
        """Test detect_transfer correctly identifies liability transfers."""
        service, transaction_repo, mapping_repo, account_repo = self._make_service()

        # Create a liability account and mapping
        liability_account = Account(
            name="Credit Card",
            account_type=AccountType.LIABILITY,
            account_number="LIA-12345",
            user_id=TEST_USER_ID,
            iban="DE89370400440532013000",
        )

        from swen.domain.integration.entities import AccountMapping

        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=liability_account.id,
            account_name="Credit Card",
            user_id=TEST_USER_ID,
        )

        mapping_repo.find_by_iban.return_value = mapping
        account_repo.find_by_id.return_value = liability_account

        # Create a bank transaction to the credit card
        from swen.domain.banking.value_objects import BankTransaction
        from datetime import date

        bank_tx = BankTransaction(
            amount=Decimal("-50.00"),
            currency="EUR",
            booking_date=date.today(),
            value_date=date.today(),
            purpose="Credit Card Payment",
            applicant_iban="DE89370400440532013000",
            applicant_name="Credit Card",
        )

        # Act
        context = await service.detect_transfer(bank_tx)

        # Assert
        assert context.is_internal_transfer is True
        assert context.is_liability_transfer is True
        assert context.is_asset_transfer is False
        assert context.can_reconcile is False  # Liabilities can't be reconciled
        assert context.counterparty_account == liability_account
