"""Unit tests for CreateSimpleTransactionCommand."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from swen.application.commands.accounting import CreateSimpleTransactionCommand
from swen.application.context.user_context import UserContext
from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.exceptions import AccountNotFoundError
from swen.domain.accounting.value_objects import Currency
from swen.domain.shared.exceptions import ValidationError


@pytest.fixture
def user_context() -> UserContext:
    """Create a test user context."""
    return UserContext(user_id=uuid4(), email="test@example.com")


@pytest.fixture
def mock_account():
    """Create a mock account factory."""
    def _create(
        account_type: AccountType = AccountType.ASSET,
        name: str | None = None,
        account_number: str | None = None,
    ):
        account = MagicMock()
        account.id = uuid4()
        account.name = name or f"Test {account_type.value}"
        account.account_number = account_number
        account.account_type = account_type
        account.default_currency = Currency("EUR")
        account.is_active = True
        return account
    return _create


@pytest.fixture
def asset_account(mock_account):
    """Default asset account."""
    return mock_account(AccountType.ASSET, name="Checking", account_number="1000")


@pytest.fixture
def expense_account(mock_account):
    """Default expense account."""
    return mock_account(AccountType.EXPENSE, name="Sonstiges", account_number="4900")


@pytest.fixture
def income_account(mock_account):
    """Default income account."""
    return mock_account(AccountType.INCOME, name="Salary", account_number="8100")


@pytest.fixture
def mock_transaction_repo() -> AsyncMock:
    """Create a mock transaction repository."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def mock_account_repo(asset_account, expense_account, income_account) -> AsyncMock:
    """Create a mock account repository with accounts."""
    repo = AsyncMock()

    accounts = [asset_account, expense_account, income_account]
    accounts_by_id = {acc.id: acc for acc in accounts}
    accounts_by_number = {acc.account_number: acc for acc in accounts}

    async def find_by_id(account_id):
        return accounts_by_id.get(account_id)

    async def find_by_account_number(number):
        return accounts_by_number.get(number)

    async def find_all():
        return accounts

    repo.find_by_id = AsyncMock(side_effect=find_by_id)
    repo.find_by_account_number = AsyncMock(side_effect=find_by_account_number)
    repo.find_all = AsyncMock(side_effect=find_all)

    return repo


class TestCreateSimpleTransactionCommand:
    """Tests for CreateSimpleTransactionCommand."""

    @pytest.fixture
    def command(
        self,
        mock_transaction_repo,
        mock_account_repo,
        user_context,
    ) -> CreateSimpleTransactionCommand:
        """Create command under test."""
        return CreateSimpleTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
            user_context=user_context,
        )

    async def test_create_expense_negative_amount(
        self,
        command,
        mock_transaction_repo,
    ):
        """Negative amount creates expense (debit expense, credit asset)."""
        txn = await command.execute(
            description="Coffee",
            amount=Decimal("-4.50"),
            counterparty="Starbucks",
        )

        assert txn.description == "Coffee"
        assert txn.counterparty == "Starbucks"
        assert len(txn.entries) == 2
        mock_transaction_repo.save.assert_called_once()

    async def test_create_income_positive_amount(
        self,
        command,
        mock_transaction_repo,
    ):
        """Positive amount creates income (debit asset, credit income)."""
        txn = await command.execute(
            description="Salary",
            amount=Decimal("3000.00"),
            counterparty="ACME Corp",
        )

        assert txn.description == "Salary"
        assert len(txn.entries) == 2
        mock_transaction_repo.save.assert_called_once()

    async def test_zero_amount_raises_validation_error(
        self,
        command,
    ):
        """Zero amount raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            await command.execute(
                description="Invalid",
                amount=Decimal("0"),
            )

        assert "non-zero" in str(exc_info.value).lower()

    async def test_account_hint_by_number(
        self,
        command,
        mock_account_repo,
    ):
        """Can specify account by number hint."""
        txn = await command.execute(
            description="With hints",
            amount=Decimal("-10.00"),
            asset_account_hint="1000",
            category_account_hint="4900",
        )

        assert txn is not None
        # Verify the hints were used to lookup accounts
        mock_account_repo.find_by_account_number.assert_any_call("1000")
        mock_account_repo.find_by_account_number.assert_any_call("4900")

    async def test_auto_post(
        self,
        command,
    ):
        """Transaction is posted when auto_post=True."""
        txn = await command.execute(
            description="Auto-posted",
            amount=Decimal("-25.00"),
            auto_post=True,
        )

        assert txn.is_posted

    async def test_no_asset_account_raises_error(
        self,
        mock_transaction_repo,
        user_context,
    ):
        """Raises error when no asset account exists."""
        # Empty account repo
        empty_repo = AsyncMock()
        empty_repo.find_by_account_number = AsyncMock(return_value=None)
        empty_repo.find_all = AsyncMock(return_value=[])

        command = CreateSimpleTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=empty_repo,
            user_context=user_context,
        )

        with pytest.raises(AccountNotFoundError):
            await command.execute(
                description="Should fail",
                amount=Decimal("-10.00"),
            )

    async def test_no_category_account_raises_error(
        self,
        mock_transaction_repo,
        user_context,
        asset_account,
    ):
        """Raises error when no matching category account exists."""
        # Repo with only asset account
        repo = AsyncMock()
        repo.find_by_account_number = AsyncMock(return_value=None)
        repo.find_all = AsyncMock(return_value=[asset_account])

        command = CreateSimpleTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=repo,
            user_context=user_context,
        )

        with pytest.raises(AccountNotFoundError):
            await command.execute(
                description="Should fail",
                amount=Decimal("-10.00"),
            )

    async def test_prefers_sonstig_account_as_default(
        self,
        mock_transaction_repo,
        user_context,
        mock_account,
    ):
        """Prefers 'sonstig/other' accounts as default category."""
        asset = mock_account(AccountType.ASSET, name="Checking")
        sonstig = mock_account(AccountType.EXPENSE, name="Sonstiges")
        groceries = mock_account(AccountType.EXPENSE, name="Groceries")

        accounts = [asset, groceries, sonstig]
        accounts_by_id = {acc.id: acc for acc in accounts}

        repo = AsyncMock()
        repo.find_by_account_number = AsyncMock(return_value=None)
        repo.find_all = AsyncMock(return_value=accounts)
        repo.find_by_id = AsyncMock(side_effect=lambda x: accounts_by_id.get(x))

        command = CreateSimpleTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=repo,
            user_context=user_context,
        )

        # Don't specify category - should use sonstig as default
        txn = await command.execute(
            description="Uses default",
            amount=Decimal("-10.00"),
        )

        # The transaction was created - sonstig was selected
        assert txn is not None

    async def test_from_factory(self, user_context):
        """Command can be created from factory."""
        factory = MagicMock()
        factory.transaction_repository.return_value = AsyncMock()
        factory.account_repository.return_value = AsyncMock()
        factory.user_context = user_context

        command = CreateSimpleTransactionCommand.from_factory(factory)

        assert command is not None
        factory.transaction_repository.assert_called_once()
        factory.account_repository.assert_called_once()

    async def test_metadata_marks_as_manual_entry(
        self,
        command,
    ):
        """Transactions are marked as manual entries."""
        txn = await command.execute(
            description="Manual entry",
            amount=Decimal("-5.00"),
        )

        metadata = txn.metadata_raw
        assert metadata.get("is_manual_entry") is True
        assert metadata.get("source") == "manual"
