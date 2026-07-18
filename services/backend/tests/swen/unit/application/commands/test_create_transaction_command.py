"""Unit tests for CreateTransactionCommand."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from swen.application.accounting.commands import CreateTransactionCommand
from swen.application.accounting.dtos import (
    TransactionDTO,
    TransactionToCreateDTO,
)
from swen.application.accounting.dtos.transactions_dto import JournalEntryToCreateDTO
from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.exceptions import AccountNotFoundError
from swen.domain.accounting.value_objects import Currency
from swen.domain.shared.current_user import CurrentUser


@pytest.fixture
def current_user() -> CurrentUser:
    """Create a test user context."""
    return CurrentUser(user_id=uuid4(), email="test@example.com")


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
        current_user,
    ) -> CreateTransactionCommand:
        """Create command under test."""
        return CreateTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
            current_user=current_user,
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

        dto = TransactionToCreateDTO(
            description="Test expense",
            entries=[
                JournalEntryToCreateDTO(
                    account_id=expense.id, debit=Decimal("50.00"), credit=Decimal("0")
                ),
                JournalEntryToCreateDTO(
                    account_id=asset.id, debit=Decimal("0"), credit=Decimal("50.00")
                ),
            ],
            counterparty="Test Merchant",
        )

        created = await command.execute(dto)

        assert created.description == "Test expense"
        assert created.counterparty == "Test Merchant"
        assert len(created.entries) == 2
        assert not created.is_posted
        mock_transaction_repo.save.assert_called_once()

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

        dto = TransactionToCreateDTO(
            description="Split purchase",
            entries=[
                JournalEntryToCreateDTO(
                    account_id=expense1.id, debit=Decimal("30.00"), credit=Decimal("0")
                ),
                JournalEntryToCreateDTO(
                    account_id=expense2.id, debit=Decimal("20.00"), credit=Decimal("0")
                ),
                JournalEntryToCreateDTO(
                    account_id=asset.id, debit=Decimal("0"), credit=Decimal("50.00")
                ),
            ],
        )

        created = await command.execute(dto)

        assert len(created.entries) == 3
        mock_transaction_repo.save.assert_called_once()

    async def test_create_and_auto_post(
        self,
        command,
        mock_account_repo,
    ):
        """Transaction is posted when auto_post=True."""
        asset = mock_account_repo._asset_account
        expense = mock_account_repo._expense_account

        dto = TransactionToCreateDTO(
            description="Auto-posted",
            entries=[
                JournalEntryToCreateDTO(
                    account_id=expense.id, debit=Decimal("25.00"), credit=Decimal("0")
                ),
                JournalEntryToCreateDTO(
                    account_id=asset.id, debit=Decimal("0"), credit=Decimal("25.00")
                ),
            ],
            auto_post=True,
        )

        created = await command.execute(dto)

        assert created.is_posted

    async def test_account_not_found_raises_error(
        self,
        command,
    ):
        """Raises AccountNotFoundError for non-existent account."""
        fake_id = uuid4()

        dto = TransactionToCreateDTO(
            description="Should fail",
            entries=[
                JournalEntryToCreateDTO(
                    account_id=fake_id, debit=Decimal("100.00"), credit=Decimal("0")
                ),
                JournalEntryToCreateDTO(
                    account_id=fake_id, debit=Decimal("0"), credit=Decimal("100.00")
                ),
            ],
        )

        with pytest.raises(AccountNotFoundError):
            await command.execute(dto)

    async def test_metadata_is_set(
        self,
        command,
        mock_account_repo,
    ):
        """Transaction metadata includes source tracking."""
        asset = mock_account_repo._asset_account
        expense = mock_account_repo._expense_account

        dto = TransactionToCreateDTO(
            description="With metadata",
            entries=[
                JournalEntryToCreateDTO(
                    account_id=expense.id, debit=Decimal("10.00"), credit=Decimal("0")
                ),
                JournalEntryToCreateDTO(
                    account_id=asset.id, debit=Decimal("0"), credit=Decimal("10.00")
                ),
            ],
            source="bank_import",
            is_manual_entry=True,
        )

        created = await command.execute(dto)

        assert created.metadata.get("source") == "bank_import"
        assert created.metadata.get("is_manual_entry") is True

    async def test_default_source_is_manual(
        self,
        command,
        mock_account_repo,
    ):
        """Default source is MANUAL."""
        asset = mock_account_repo._asset_account
        expense = mock_account_repo._expense_account

        dto = TransactionToCreateDTO(
            description="Default source",
            entries=[
                JournalEntryToCreateDTO(
                    account_id=expense.id, debit=Decimal("10.00"), credit=Decimal("0")
                ),
                JournalEntryToCreateDTO(
                    account_id=asset.id, debit=Decimal("0"), credit=Decimal("10.00")
                ),
            ],
        )

        created = await command.execute(dto)

        assert created.metadata.get("source") == "manual"

    async def test_from_factory(self, current_user):
        """Command can be created from factory."""
        factory = MagicMock()
        factory.transaction_repository.return_value = AsyncMock()
        factory.account_repository.return_value = AsyncMock()
        factory.current_user = current_user

        command = CreateTransactionCommand.from_factory(factory)

        assert command is not None
        factory.transaction_repository.assert_called_once()
        factory.account_repository.assert_called_once()

    async def test_command_returns_dto_not_entity(
        self,
        command,
        mock_account_repo,
    ):
        """Command returns TransactionCreatedDTO, not domain Transaction."""
        asset = mock_account_repo._asset_account
        expense = mock_account_repo._expense_account

        dto = TransactionToCreateDTO(
            description="DTO test",
            entries=[
                JournalEntryToCreateDTO(
                    account_id=expense.id, debit=Decimal("10.00"), credit=Decimal("0")
                ),
                JournalEntryToCreateDTO(
                    account_id=asset.id, debit=Decimal("0"), credit=Decimal("10.00")
                ),
            ],
        )

        created = await command.execute(dto)

        assert isinstance(created, TransactionDTO)
        assert created.id is not None
        assert created.description == "DTO test"
        assert len(created.entries) == 2
        assert created.entries[0].account_name == expense.name
        assert created.entries[0].debit == Decimal("10.00")
        assert created.entries[1].credit == Decimal("10.00")
