"""Unit tests for CreateTransactionCommand."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from swen.application.commands.accounting import CreateTransactionCommand
from swen.application.context.user_context import UserContext
from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.exceptions import AccountNotFoundError
from swen.domain.accounting.value_objects import (
    Currency,
    JournalEntryInput,
    TransactionSource,
)


@pytest.fixture
def user_context() -> UserContext:
    """Create a test user context."""
    return UserContext(user_id=uuid4(), email="test@example.com")


@pytest.fixture
def mock_account():
    """Create a mock account."""
    def _create(account_type: AccountType = AccountType.ASSET):
        account = MagicMock()
        account.id = uuid4()
        account.name = f"Test {account_type.value}"
        account.account_type = account_type
        account.default_currency = Currency("EUR")
        account.is_active = True
        return account
    return _create


@pytest.fixture
def mock_transaction_repo() -> AsyncMock:
    """Create a mock transaction repository."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def mock_account_repo(mock_account) -> AsyncMock:
    """Create a mock account repository."""
    repo = AsyncMock()

    # Create accounts that will be returned
    asset_account = mock_account(AccountType.ASSET)
    expense_account = mock_account(AccountType.EXPENSE)

    # Map account IDs to accounts
    accounts = {
        asset_account.id: asset_account,
        expense_account.id: expense_account,
    }

    async def find_by_id(account_id):
        return accounts.get(account_id)

    repo.find_by_id = AsyncMock(side_effect=find_by_id)
    repo._accounts = accounts  # Expose for test access
    repo._asset_account = asset_account
    repo._expense_account = expense_account

    return repo


class TestCreateTransactionCommand:
    """Tests for CreateTransactionCommand."""

    @pytest.fixture
    def command(
        self,
        mock_transaction_repo,
        mock_account_repo,
        user_context,
    ) -> CreateTransactionCommand:
        """Create command under test."""
        return CreateTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
            user_context=user_context,
        )

    async def test_create_simple_two_entry_transaction(
        self,
        command,
        mock_transaction_repo,
        mock_account_repo,
    ):
        """Create a basic two-entry transaction."""
        asset = mock_account_repo._asset_account
        expense = mock_account_repo._expense_account

        entries = [
            JournalEntryInput.debit_entry(expense.id, Decimal("50.00")),
            JournalEntryInput.credit_entry(asset.id, Decimal("50.00")),
        ]

        txn = await command.execute(
            description="Test expense",
            entries=entries,
            counterparty="Test Merchant",
        )

        assert txn.description == "Test expense"
        assert txn.counterparty == "Test Merchant"
        assert len(txn.entries) == 2
        assert not txn.is_posted
        mock_transaction_repo.save.assert_called_once_with(txn)

    async def test_create_multi_entry_transaction(
        self,
        command,
        mock_transaction_repo,
        mock_account_repo,
        mock_account,
    ):
        """Create a transaction with more than 2 entries (split)."""
        asset = mock_account_repo._asset_account
        expense1 = mock_account_repo._expense_account
        expense2 = mock_account(AccountType.EXPENSE)

        # Add second expense to repo
        mock_account_repo._accounts[expense2.id] = expense2

        entries = [
            JournalEntryInput.debit_entry(expense1.id, Decimal("30.00")),
            JournalEntryInput.debit_entry(expense2.id, Decimal("20.00")),
            JournalEntryInput.credit_entry(asset.id, Decimal("50.00")),
        ]

        txn = await command.execute(
            description="Split purchase",
            entries=entries,
        )

        assert len(txn.entries) == 3
        mock_transaction_repo.save.assert_called_once()

    async def test_create_and_auto_post(
        self,
        command,
        mock_account_repo,
    ):
        """Transaction is posted when auto_post=True."""
        asset = mock_account_repo._asset_account
        expense = mock_account_repo._expense_account

        entries = [
            JournalEntryInput.debit_entry(expense.id, Decimal("25.00")),
            JournalEntryInput.credit_entry(asset.id, Decimal("25.00")),
        ]

        txn = await command.execute(
            description="Auto-posted",
            entries=entries,
            auto_post=True,
        )

        assert txn.is_posted

    async def test_account_not_found_raises_error(
        self,
        command,
    ):
        """Raises AccountNotFoundError for non-existent account."""
        fake_id = uuid4()

        entries = [
            JournalEntryInput.debit_entry(fake_id, Decimal("100.00")),
            JournalEntryInput.credit_entry(fake_id, Decimal("100.00")),
        ]

        with pytest.raises(AccountNotFoundError):
            await command.execute(
                description="Should fail",
                entries=entries,
            )

    async def test_metadata_is_set(
        self,
        command,
        mock_account_repo,
    ):
        """Transaction metadata includes source tracking."""
        asset = mock_account_repo._asset_account
        expense = mock_account_repo._expense_account

        entries = [
            JournalEntryInput.debit_entry(expense.id, Decimal("10.00")),
            JournalEntryInput.credit_entry(asset.id, Decimal("10.00")),
        ]

        txn = await command.execute(
            description="With metadata",
            entries=entries,
            source=TransactionSource.BANK_IMPORT,
            is_manual_entry=True,
        )

        metadata = txn.metadata_raw
        assert metadata.get("source") == "bank_import"
        assert metadata.get("is_manual_entry") is True

    async def test_default_source_is_manual(
        self,
        command,
        mock_account_repo,
    ):
        """Default source is MANUAL."""
        asset = mock_account_repo._asset_account
        expense = mock_account_repo._expense_account

        entries = [
            JournalEntryInput.debit_entry(expense.id, Decimal("10.00")),
            JournalEntryInput.credit_entry(asset.id, Decimal("10.00")),
        ]

        txn = await command.execute(
            description="Default source",
            entries=entries,
        )

        assert txn.metadata_raw.get("source") == "manual"

    async def test_from_factory(self, user_context):
        """Command can be created from factory."""
        factory = MagicMock()
        factory.transaction_repository.return_value = AsyncMock()
        factory.account_repository.return_value = AsyncMock()
        factory.user_context = user_context

        command = CreateTransactionCommand.from_factory(factory)

        assert command is not None
        factory.transaction_repository.assert_called_once()
        factory.account_repository.assert_called_once()
