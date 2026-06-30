"""Unit tests for CreateSimpleTransactionCommand."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from swen.application.accounting.commands import CreateSimpleTransactionCommand
from swen.application.accounting.dtos import SimpleTransactionToCreateDTO
from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.exceptions import (
    AccountNotFoundError,
    InvalidAccountTypeError,
)
from swen.domain.accounting.value_objects import Currency
from swen.domain.shared.current_user import CurrentUser
from swen.domain.shared.exceptions import ValidationError


@pytest.fixture
def current_user() -> CurrentUser:
    """Create a test user context."""
    return CurrentUser(user_id=uuid4(), email="test@example.com")


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
        # Configure type-checking methods to return proper booleans
        account.is_asset_account.return_value = account_type == AccountType.ASSET
        account.is_liability_account.return_value = (
            account_type == AccountType.LIABILITY
        )
        account.is_expense_account.return_value = account_type == AccountType.EXPENSE
        account.is_income_account.return_value = account_type == AccountType.INCOME
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
def liability_account(mock_account):
    """Default liability account (credit card)."""
    return mock_account(
        AccountType.LIABILITY, name="VISA Credit Card", account_number="2100"
    )


@pytest.fixture
def mock_transaction_repo() -> AsyncMock:
    """Create a mock transaction repository."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def mock_account_repo(
    asset_account,
    expense_account,
    income_account,
    liability_account,
) -> AsyncMock:
    """Create a mock account repository with accounts."""
    repo = AsyncMock()

    accounts = [
        asset_account,
        expense_account,
        income_account,
        liability_account,
    ]
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
        current_user,
    ) -> CreateSimpleTransactionCommand:
        """Create command under test."""
        return CreateSimpleTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=mock_account_repo,
            current_user=current_user,
        )

    async def test_create_expense_negative_amount(
        self,
        command,
        mock_transaction_repo,
        expense_account,
        asset_account,
    ):
        """Negative amount creates expense (debit expense, credit asset)."""
        dto = SimpleTransactionToCreateDTO(
            description="Coffee",
            amount=Decimal("-4.50"),
            payment_account="1000",
            counter_account="4900",
            counterparty="Starbucks",
        )
        txn = await command.execute(dto)

        assert txn.description == "Coffee"
        assert txn.counterparty == "Starbucks"
        assert len(txn.entries) == 2

        # Granular entry assertion: expense account gets debit, asset gets credit
        assert txn.entries[0].account_name == expense_account.name
        assert txn.entries[0].debit == Decimal("4.50")
        assert txn.entries[0].credit is None

        assert txn.entries[1].account_name == asset_account.name
        assert txn.entries[1].debit is None
        assert txn.entries[1].credit == Decimal("4.50")

        mock_transaction_repo.save.assert_called_once()

    async def test_create_income_positive_amount(
        self,
        command,
        asset_account,
        income_account,
    ):
        """Positive amount creates income (debit asset, credit income)."""
        dto = SimpleTransactionToCreateDTO(
            description="Salary",
            amount=Decimal("3000.00"),
            payment_account="1000",
            counter_account="8100",
            counterparty="ACME Corp",
        )
        txn = await command.execute(dto)

        assert txn.description == "Salary"

        # Granular entry assertion: asset gets debit, income gets credit
        assert txn.entries[0].account_name == asset_account.name
        assert txn.entries[0].debit == Decimal("3000.00")
        assert txn.entries[0].credit is None

        assert txn.entries[1].account_name == income_account.name
        assert txn.entries[1].debit is None
        assert txn.entries[1].credit == Decimal("3000.00")

    async def test_expense_creates_debit_expense_credit_asset(
        self,
        command,
        asset_account,
        expense_account,
    ):
        """Expense: Debit expense account, Credit asset account."""
        dto = SimpleTransactionToCreateDTO(
            description="Groceries",
            amount=Decimal("-50.00"),
            payment_account="1000",
            counter_account="4900",
            counterparty="Supermarket",
        )
        txn = await command.execute(dto)

        assert len(txn.entries) == 2

        # First entry: Debit expense
        assert txn.entries[0].account_name == expense_account.name
        assert txn.entries[0].debit == Decimal("50.00")
        assert txn.entries[0].credit is None

        # Second entry: Credit asset
        assert txn.entries[1].account_name == asset_account.name
        assert txn.entries[1].debit is None
        assert txn.entries[1].credit == Decimal("50.00")

    async def test_income_creates_debit_asset_credit_income(
        self,
        command,
        asset_account,
        income_account,
    ):
        """Income: Debit asset account, Credit income account."""
        dto = SimpleTransactionToCreateDTO(
            description="Income",
            amount=Decimal("50.00"),
            payment_account="1000",
            counter_account="8100",
            counterparty="Employer",
        )
        txn = await command.execute(dto)

        assert len(txn.entries) == 2

        # First entry: Debit asset
        assert txn.entries[0].account_name == asset_account.name
        assert txn.entries[0].debit == Decimal("50.00")
        assert txn.entries[0].credit is None

        # Second entry: Credit income
        assert txn.entries[1].account_name == income_account.name
        assert txn.entries[1].debit is None
        assert txn.entries[1].credit == Decimal("50.00")

    async def test_expense_with_liability_payment(
        self,
        command,
        liability_account,
        expense_account,
    ):
        """Expense with credit card: Debit expense, Credit liability."""
        dto = SimpleTransactionToCreateDTO(
            description="Groceries on card",
            amount=Decimal("-50.00"),
            payment_account="2100",
            counter_account="4900",
            counterparty="Supermarket",
        )
        txn = await command.execute(dto)

        assert len(txn.entries) == 2
        assert txn.entries[0].account_name == expense_account.name
        assert txn.entries[0].debit == Decimal("50.00")
        assert txn.entries[0].credit is None
        assert txn.entries[1].account_name == liability_account.name
        assert txn.entries[1].debit is None
        assert txn.entries[1].credit == Decimal("50.00")

    async def test_rejects_invalid_payment_account_type(
        self,
        command,
        expense_account,
        income_account,
    ):
        """Payment account must be Asset or Liability."""
        dto = SimpleTransactionToCreateDTO(
            description="Should fail",
            amount=Decimal("-10.00"),
            payment_account="4900",  # Expense account, not allowed
            counter_account="8100",
            counterparty="Test",
        )
        with pytest.raises(InvalidAccountTypeError, match="asset.*liability"):
            await command.execute(dto)

    async def test_rejects_mismatched_category_for_expense(
        self,
        command,
        asset_account,
        income_account,
    ):
        """Expense direction requires Expense account type."""
        dto = SimpleTransactionToCreateDTO(
            description="Should fail",
            amount=Decimal("-10.00"),
            payment_account="1000",
            counter_account="8100",  # Income account, wrong for expense
            counterparty="Test",
        )
        with pytest.raises(InvalidAccountTypeError, match="expense"):
            await command.execute(dto)

    async def test_rejects_mismatched_category_for_income(
        self,
        command,
        asset_account,
        expense_account,
    ):
        """Income direction requires Income account type."""
        dto = SimpleTransactionToCreateDTO(
            description="Should fail",
            amount=Decimal("10.00"),
            payment_account="1000",
            counter_account="4900",  # Expense account, wrong for income
            counterparty="Test",
        )
        with pytest.raises(InvalidAccountTypeError, match="income"):
            await command.execute(dto)

    async def test_zero_amount_raises_validation_error(
        self,
        command,
    ):
        """Zero amount raises ValidationError."""
        dto = SimpleTransactionToCreateDTO(
            description="Invalid",
            amount=Decimal("0"),
            payment_account="1000",
            counter_account="4900",
            counterparty="Test",
        )
        with pytest.raises(ValidationError) as exc_info:
            await command.execute(dto)

        assert "non-zero" in str(exc_info.value).lower()

    async def test_account_lookup_by_number(
        self,
        command,
        mock_account_repo,
    ):
        """Looks up accounts by account number."""
        dto = SimpleTransactionToCreateDTO(
            description="With accounts",
            amount=Decimal("-10.00"),
            payment_account="1000",
            counter_account="4900",
            counterparty="Test",
        )
        txn = await command.execute(dto)

        assert txn is not None
        # Verify the account numbers were used to lookup accounts
        mock_account_repo.find_by_account_number.assert_any_call("1000")
        mock_account_repo.find_by_account_number.assert_any_call("4900")

    async def test_auto_post(
        self,
        command,
    ):
        """Transaction is posted when auto_post=True."""
        dto = SimpleTransactionToCreateDTO(
            description="Auto-posted",
            amount=Decimal("-25.00"),
            payment_account="1000",
            counter_account="4900",
            counterparty="Test",
            auto_post=True,
        )
        txn = await command.execute(dto)

        assert txn.is_posted

    async def test_missing_payment_account_raises_error(
        self,
        mock_transaction_repo,
        current_user,
    ):
        """Raises error when the payment account is not found."""
        # Empty account repo
        empty_repo = AsyncMock()
        empty_repo.find_by_account_number = AsyncMock(return_value=None)

        command = CreateSimpleTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=empty_repo,
            current_user=current_user,
        )

        dto = SimpleTransactionToCreateDTO(
            description="Should fail",
            amount=Decimal("-10.00"),
            payment_account="9999",
            counter_account="4900",
            counterparty="Test",
        )
        with pytest.raises(AccountNotFoundError):
            await command.execute(dto)

    async def test_missing_category_account_raises_error(
        self,
        mock_transaction_repo,
        current_user,
        asset_account,
    ):
        """Raises error when the category account is not found."""
        # Repo with only asset account
        repo = AsyncMock()
        repo.find_by_account_number = AsyncMock(
            side_effect=lambda n: asset_account if n == "1000" else None
        )

        command = CreateSimpleTransactionCommand(
            transaction_repository=mock_transaction_repo,
            account_repository=repo,
            current_user=current_user,
        )

        dto = SimpleTransactionToCreateDTO(
            description="Should fail",
            amount=Decimal("-10.00"),
            payment_account="1000",
            counter_account="9999",
            counterparty="Test",
        )
        with pytest.raises(AccountNotFoundError):
            await command.execute(dto)

    async def test_from_factory(self, current_user):
        """Command can be created from factory."""
        factory = MagicMock()
        factory.transaction_repository.return_value = AsyncMock()
        factory.account_repository.return_value = AsyncMock()
        factory.current_user = current_user

        command = CreateSimpleTransactionCommand.from_factory(factory)

        assert command is not None
        factory.transaction_repository.assert_called_once()
        factory.account_repository.assert_called_once()

    async def test_metadata_marks_as_manual_entry(
        self,
        command,
    ):
        """Transactions are marked as manual entries."""
        dto = SimpleTransactionToCreateDTO(
            description="Manual entry",
            amount=Decimal("-5.00"),
            payment_account="1000",
            counter_account="4900",
            counterparty="Test",
        )
        txn = await command.execute(dto)

        metadata = txn.metadata
        assert metadata.get("is_manual_entry") is True
        assert metadata.get("source") == "manual"
