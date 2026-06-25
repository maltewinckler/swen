"""Unit tests for EditTransactionCommand."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from swen.application.accounting.commands import EditTransactionCommand
from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.exceptions import (
    AccountNotFoundError,
    TransactionNotFoundError,
)
from swen.domain.accounting.value_objects import Currency, JournalEntryInput, Money
from swen.domain.shared.exceptions import ValidationError


@dataclass
class DomainCallTracker:
    """Tracks calls to domain service methods."""

    replace_count: int = 0
    change_count: int = 0
    metadata_count: int = 0
    metadata_applied: dict[str, Any] = field(default_factory=dict)


@pytest.fixture
def mock_account():
    """Create a mock account."""

    def _create(account_type: AccountType = AccountType.ASSET, name: str | None = None):
        account = MagicMock()
        account.id = uuid4()
        account.name = name or f"Test {account_type.value}"
        account.account_type = account_type
        account.default_currency = Currency("EUR")
        account.is_active = True
        return account

    return _create


@pytest.fixture
def mock_transaction(mock_account):
    """Create a mock transaction with entries."""

    def _create(is_posted: bool = False):
        asset = mock_account(AccountType.ASSET, "Checking")
        expense = mock_account(AccountType.EXPENSE, "Groceries")

        # Create mock entries
        debit_entry = MagicMock()
        debit_entry.id = uuid4()
        debit_entry.account = expense
        debit_entry.debit = Money(Decimal("50.00"), Currency("EUR"))
        debit_entry.credit = Money(Decimal("0"), Currency("EUR"))
        debit_entry.is_debit.return_value = True

        credit_entry = MagicMock()
        credit_entry.id = uuid4()
        credit_entry.account = asset
        credit_entry.debit = Money(Decimal("0"), Currency("EUR"))
        credit_entry.credit = Money(Decimal("50.00"), Currency("EUR"))
        credit_entry.is_debit.return_value = False

        # Create mock transaction
        txn = MagicMock()
        txn.id = uuid4()
        txn.description = "Original description"
        txn.counterparty = "Original counterparty"
        txn.is_posted = is_posted
        txn.entries = [debit_entry, credit_entry]
        txn._asset_account = asset
        txn._expense_account = expense

        return txn

    return _create


@pytest.fixture
def mock_transaction_repo(mock_transaction) -> AsyncMock:
    """Create a mock transaction repository."""
    repo = AsyncMock()
    txn = mock_transaction(is_posted=False)
    repo.find_by_id = AsyncMock(return_value=txn)
    repo.save = AsyncMock()
    repo._transaction = txn
    return repo


@pytest.fixture
def mock_account_repo(mock_account) -> AsyncMock:
    """Create a mock account repository."""
    repo = AsyncMock()

    # Create accounts that can be returned
    asset_account = mock_account(AccountType.ASSET, "Checking")
    expense_account = mock_account(AccountType.EXPENSE, "Groceries")
    income_account = mock_account(AccountType.INCOME, "Salary")
    expense_account2 = mock_account(AccountType.EXPENSE, "Restaurant")

    # Map account IDs to accounts
    accounts = {
        asset_account.id: asset_account,
        expense_account.id: expense_account,
        income_account.id: income_account,
        expense_account2.id: expense_account2,
    }

    async def find_by_id(account_id):
        return accounts.get(account_id)

    repo.find_by_id = AsyncMock(side_effect=find_by_id)
    repo._accounts = accounts
    repo._asset_account = asset_account
    repo._expense_account = expense_account
    repo._income_account = income_account
    repo._expense_account2 = expense_account2

    return repo


class TestEditTransactionCommand:
    """Tests for EditTransactionCommand coordinator."""

    async def test_load_transaction_not_found(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Raises TransactionNotFoundError when transaction doesn't exist."""
        mock_transaction_repo.find_by_id.return_value = None
        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        with pytest.raises(TransactionNotFoundError):
            await command.execute(transaction_id=uuid4())

    async def test_unpost_if_posted(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Transaction is unposted before edits if it was posted."""
        txn = mock_transaction_repo._transaction
        txn.is_posted = True

        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        await command.execute(
            transaction_id=txn.id,
            description="New description",
            repost=False,
        )

        txn.unpost.assert_called_once()

    async def test_repost_if_was_posted_and_requested(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Transaction is reposted after edits if it was posted and repost=True."""
        txn = mock_transaction_repo._transaction
        txn.is_posted = True

        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        await command.execute(
            transaction_id=txn.id,
            description="New description",
            repost=True,
        )

        txn.unpost.assert_called_once()
        txn.post.assert_called_once()

    async def test_save_is_called(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Transaction is saved after edits."""
        txn = mock_transaction_repo._transaction

        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        await command.execute(
            transaction_id=txn.id,
            description="New description",
        )

        mock_transaction_repo.save.assert_called_once_with(txn)

    async def test_entries_and_category_mutually_exclusive(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Cannot specify both entries and counter_account_id."""
        txn = mock_transaction_repo._transaction
        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        with pytest.raises(ValueError) as exc_info:
            await command.execute(
                transaction_id=txn.id,
                entries=[
                    JournalEntryInput.debit_entry(
                        mock_account_repo._expense_account.id,
                        Decimal("50.00"),
                    ),
                    JournalEntryInput.credit_entry(
                        mock_account_repo._asset_account.id,
                        Decimal("50.00"),
                    ),
                ],
                counter_account_id=mock_account_repo._expense_account2.id,
            )

        assert "cannot specify both" in str(exc_info.value).lower()

    # =========================================================================
    # _update_description tests
    # =========================================================================

    async def test_update_description(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Description is updated via transaction method."""
        txn = mock_transaction_repo._transaction

        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        await command.execute(
            transaction_id=txn.id,
            description="Updated description",
        )

        txn.update_description.assert_called_once_with("Updated description")

    # =========================================================================
    # _update_counterparty tests
    # =========================================================================

    async def test_update_counterparty(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Counterparty is updated via transaction method."""
        txn = mock_transaction_repo._transaction

        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        await command.execute(
            transaction_id=txn.id,
            counterparty="New Merchant",
        )

        txn.update_counterparty.assert_called_once_with("New Merchant")

    # =========================================================================
    # _update_metadata tests
    # =========================================================================

    async def test_update_metadata(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Metadata is updated via domain service."""
        txn = mock_transaction_repo._transaction
        tracker = DomainCallTracker()

        def mock_update_metadata(transaction, metadata):
            tracker.metadata_count += 1
            tracker.metadata_applied.update(metadata)

        with patch(
            "swen.application.accounting.commands.edit_transaction_command.TransactionEditService.update_metadata",
            staticmethod(mock_update_metadata),
        ):
            command = EditTransactionCommand(
                transaction_repository=mock_transaction_repo,
                account_repository=mock_account_repo,
            )

            await command.execute(
                transaction_id=txn.id,
                metadata={"custom_tag": "value123"},
            )

        assert tracker.metadata_count == 1
        assert tracker.metadata_applied.get("custom_tag") == "value123"

    async def test_update_metadata_rejects_reserved_keys(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Reserved metadata keys are rejected by domain service."""
        txn = mock_transaction_repo._transaction

        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        with pytest.raises(ValidationError) as exc_info:
            await command.execute(
                transaction_id=txn.id,
                metadata={"source": "hacked"},
            )

        assert "reserved" in str(exc_info.value).lower()

    # =========================================================================
    # _replace_entries tests
    # =========================================================================

    async def test_replace_entries(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Entries are replaced via domain service."""
        txn = mock_transaction_repo._transaction
        tracker = DomainCallTracker()

        def mock_replace_entries(transaction, entries, accounts):
            tracker.replace_count += 1

        with patch(
            "swen.application.accounting.commands.edit_transaction_command.TransactionEditService.replace_entries",
            staticmethod(mock_replace_entries),
        ):
            command = EditTransactionCommand(
                transaction_repository=mock_transaction_repo,
                account_repository=mock_account_repo,
            )

            entries = [
                JournalEntryInput.debit_entry(
                    mock_account_repo._expense_account.id, Decimal("75.00")
                ),
                JournalEntryInput.credit_entry(
                    mock_account_repo._asset_account.id, Decimal("75.00")
                ),
            ]

            await command.execute(
                transaction_id=txn.id,
                entries=entries,
            )

        assert tracker.replace_count == 1

    async def test_replace_entries_with_multiple(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Multi-entry replacement works (split transaction)."""
        txn = mock_transaction_repo._transaction
        tracker = DomainCallTracker()

        def mock_replace_entries(transaction, entries, accounts):
            tracker.replace_count += 1

        with patch(
            "swen.application.accounting.commands.edit_transaction_command.TransactionEditService.replace_entries",
            staticmethod(mock_replace_entries),
        ):
            command = EditTransactionCommand(
                transaction_repository=mock_transaction_repo,
                account_repository=mock_account_repo,
            )

            entries = [
                JournalEntryInput.debit_entry(
                    mock_account_repo._expense_account.id, Decimal("30.00")
                ),
                JournalEntryInput.debit_entry(
                    mock_account_repo._expense_account2.id, Decimal("20.00")
                ),
                JournalEntryInput.credit_entry(
                    mock_account_repo._asset_account.id, Decimal("50.00")
                ),
            ]

            await command.execute(
                transaction_id=txn.id,
                entries=entries,
            )

        assert tracker.replace_count == 1

    async def test_replace_entries_requires_minimum_two(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """At least 2 entries required - validated by domain service."""
        txn = mock_transaction_repo._transaction

        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        entries = [
            JournalEntryInput.debit_entry(
                mock_account_repo._expense_account.id, Decimal("50.00")
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            await command.execute(
                transaction_id=txn.id,
                entries=entries,
            )

        assert "at least 2" in str(exc_info.value).lower()

    async def test_replace_entries_account_not_found(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Raises AccountNotFoundError for unknown account."""
        txn = mock_transaction_repo._transaction
        fake_id = uuid4()

        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        entries = [
            JournalEntryInput.debit_entry(fake_id, Decimal("50.00")),
            JournalEntryInput.credit_entry(fake_id, Decimal("50.00")),
        ]

        with pytest.raises(AccountNotFoundError):
            await command.execute(
                transaction_id=txn.id,
                entries=entries,
            )

    # =========================================================================
    # _change_counter_account tests
    # =========================================================================

    async def test_change_counter_account(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Category change delegates to domain service."""
        txn = mock_transaction_repo._transaction
        tracker = DomainCallTracker()

        def mock_change_counter_account(transaction, counter_account):
            tracker.change_count += 1

        with patch(
            "swen.application.accounting.commands.edit_transaction_command.TransactionEditService.change_counter_account",
            staticmethod(mock_change_counter_account),
        ):
            command = EditTransactionCommand(
                transaction_repository=mock_transaction_repo,
                account_repository=mock_account_repo,
            )

            await command.execute(
                transaction_id=txn.id,
                counter_account_id=mock_account_repo._expense_account2.id,
            )

        assert tracker.change_count == 1

    async def test_change_counter_account_with_liability_account(
        self,
        mock_transaction_repo,
        mock_account_repo,
        mock_account,
    ):
        """Category change works when payment account is a liability (credit card)."""
        # Create a liability account
        liability_account = mock_account(AccountType.LIABILITY, "Credit Card")
        expense_account = mock_account(AccountType.EXPENSE, "Groceries")
        new_expense_account = mock_account(AccountType.EXPENSE, "Restaurant")

        # Add accounts to the mock repo
        mock_account_repo._accounts[liability_account.id] = liability_account
        mock_account_repo._accounts[new_expense_account.id] = new_expense_account

        # Create entries for a credit card purchase: Debit Expense / Credit Liability
        debit_entry = MagicMock()
        debit_entry.id = uuid4()
        debit_entry.account = expense_account
        debit_entry.debit = Money(Decimal("50.00"), Currency("EUR"))
        debit_entry.credit = Money(Decimal("0"), Currency("EUR"))
        debit_entry.is_debit.return_value = True

        credit_entry = MagicMock()
        credit_entry.id = uuid4()
        credit_entry.account = liability_account
        credit_entry.debit = Money(Decimal("0"), Currency("EUR"))
        credit_entry.credit = Money(Decimal("50.00"), Currency("EUR"))
        credit_entry.is_debit.return_value = False

        # Create mock transaction with liability as payment account
        txn = MagicMock()
        txn.id = uuid4()
        txn.description = "Credit card purchase"
        txn.counterparty = "Store"
        txn.is_posted = False
        txn.entries = [debit_entry, credit_entry]

        # Transaction repo
        txn_repo = AsyncMock()
        txn_repo.find_by_id = AsyncMock(return_value=txn)
        txn_repo.save = AsyncMock()

        tracker = DomainCallTracker()

        def mock_change_counter_account(transaction, counter_account):
            tracker.change_count += 1

        with patch(
            "swen.application.accounting.commands.edit_transaction_command.TransactionEditService.change_counter_account",
            staticmethod(mock_change_counter_account),
        ):
            command = EditTransactionCommand(
                transaction_repository=txn_repo,
                account_repository=mock_account_repo,
            )

            # Execute category change - should NOT raise BusinessRuleViolation
            await command.execute(
                transaction_id=txn.id,
                counter_account_id=new_expense_account.id,
            )

        # Verify the transaction was modified
        assert tracker.change_count == 1
        txn_repo.save.assert_called_once_with(txn)

    async def test_change_counter_account_account_not_found(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Raises AccountNotFoundError for unknown category account."""
        txn = mock_transaction_repo._transaction
        fake_id = uuid4()

        command = EditTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
        )

        with pytest.raises(AccountNotFoundError):
            await command.execute(
                transaction_id=txn.id,
                counter_account_id=fake_id,
            )

    # =========================================================================
    # Factory test
    # =========================================================================

    async def test_from_factory(self):
        """Command can be created from factory."""
        factory = MagicMock()
        factory.transaction_repository.return_value = AsyncMock()
        factory.account_repository.return_value = AsyncMock()

        command = EditTransactionCommand.from_factory(factory)

        assert command is not None
        factory.transaction_repository.assert_called_once()
        factory.account_repository.assert_called_once()

    # =========================================================================
    # Combined operations test
    # =========================================================================

    async def test_multiple_operations_in_one_call(
        self,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Can update description, counterparty, and entries in one call."""
        txn = mock_transaction_repo._transaction
        tracker = DomainCallTracker()

        def mock_replace_entries(transaction, entries, accounts):
            tracker.replace_count += 1

        with patch(
            "swen.application.accounting.commands.edit_transaction_command.TransactionEditService.replace_entries",
            staticmethod(mock_replace_entries),
        ):
            command = EditTransactionCommand(
                transaction_repository=mock_transaction_repo,
                account_repository=mock_account_repo,
            )

            entries = [
                JournalEntryInput.debit_entry(
                    mock_account_repo._expense_account.id, Decimal("100.00")
                ),
                JournalEntryInput.credit_entry(
                    mock_account_repo._asset_account.id, Decimal("100.00")
                ),
            ]

            await command.execute(
                transaction_id=txn.id,
                entries=entries,
                description="New description",
                counterparty="New counterparty",
            )

        # All operations should have been called
        txn.update_description.assert_called_once_with("New description")
        txn.update_counterparty.assert_called_once_with("New counterparty")
        assert tracker.replace_count == 1
        mock_transaction_repo.save.assert_called_once()
