"""
End-to-end integration tests for opening balance creation.

These tests verify the complete opening balance workflow:
1. Connect to bank (mocked)
2. Fetch transactions and current balance
3. Calculate and create opening balance
4. Persist to real database (SQLite in-memory)
5. Verify data integrity and idempotency
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from swen.application.commands.integration import TransactionSyncCommand
from swen.application.factories import BankImportTransactionFactory
from swen.application.services import (
    BankAccountImportService,
    TransactionImportService,
)
from swen.application.services.transfer_reconciliation_service import (
    TransferReconciliationService,
)
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.services import (
    OPENING_BALANCE_IBAN_KEY,
    OPENING_BALANCE_METADATA_KEY,
)
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import (
    BankAccount,
    BankCredentials,
    BankTransaction,
)
from swen.domain.integration.entities import AccountMapping
from swen.domain.integration.services import CounterAccountResolutionService
from swen.domain.integration.value_objects import ResolutionResult
from swen.domain.shared.value_objects.secure_string import SecureString
from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    BankAccountRepositorySQLAlchemy,
    BankTransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
    TransactionImportRepositorySQLAlchemy,
)
from swen.application.ports.identity import CurrentUser

# Fixed UUID for testing
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_EMAIL = "test@example.com"

# Create test user context
TEST_USER_CONTEXT = CurrentUser(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)


def _create_import_service(
    bank_account_import_service,
    counter_account_resolution_service,
    account_repo,
    transaction_repo,
    mapping_repo,
    import_repo,
):
    """Helper to create TransactionImportService with new constructor."""
    transfer_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
        mapping_repository=mapping_repo,
        account_repository=account_repo,
    )
    transaction_factory = BankImportTransactionFactory(
        current_user=TEST_USER_CONTEXT,
    )
    return TransactionImportService(
        bank_account_import_service=bank_account_import_service,
        counter_account_resolution_service=counter_account_resolution_service,
        transfer_reconciliation_service=transfer_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        current_user=TEST_USER_CONTEXT,
    )


# ============================================================================
# Test Data
# ============================================================================

IBAN = "DE89370400440532013000"
BLZ = "37040044"


def _make_credentials() -> BankCredentials:
    return BankCredentials(
        blz=BLZ,
        username=SecureString("user"),
        pin=SecureString("123456"),
        endpoint="https://fints.example.com/fints",
    )


def _make_bank_account(
    iban: str = IBAN, balance: Decimal = Decimal("1000.00"),
) -> BankAccount:
    """Create a bank account value object with balance."""
    return BankAccount(
        iban=iban,
        account_number="532013000",
        blz=BLZ,
        account_holder="Max Mustermann",
        account_type="Girokonto",
        currency="EUR",
        balance=balance,
        balance_date=datetime.now(tz=timezone.utc),
    )


def _make_bank_transactions() -> list[BankTransaction]:
    """Create sample bank transactions."""
    return [
        BankTransaction(
            booking_date=date(2025, 1, 15),
            value_date=date(2025, 1, 15),
            amount=Decimal("500.00"),  # Income
            currency="EUR",
            purpose="Salary",
            applicant_name="Employer GmbH",
        ),
        BankTransaction(
            booking_date=date(2025, 1, 20),
            value_date=date(2025, 1, 20),
            amount=Decimal("-100.00"),  # Expense
            currency="EUR",
            purpose="REWE Sagt Danke",
            applicant_name="REWE",
        ),
        BankTransaction(
            booking_date=date(2025, 1, 10),  # Earliest
            value_date=date(2025, 1, 10),
            amount=Decimal("-50.00"),
            currency="EUR",
            purpose="Coffee Shop",
            applicant_name="Starbucks",
        ),
    ]


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def integration_engine():
    """Create an async engine for integration tests."""
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )


@pytest_asyncio.fixture(scope="function")
async def integration_session(integration_engine):
    """Create a fresh database session for each test."""
    async with integration_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        integration_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    async with integration_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def setup_chart_of_accounts(integration_session):
    """Set up minimal chart of accounts needed for opening balance."""
    account_repo = AccountRepositorySQLAlchemy(integration_session, TEST_USER_CONTEXT)

    # Create the Opening Balance equity account (required)
    opening_balance_account = Account(
        name="Anfangssaldo (Opening Balance)",
        account_type=AccountType.EQUITY,
        account_number="2000",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(opening_balance_account)

    # Create income account for categorization
    income_account = Account(
        name="Sonstige Einnahmen (Other Income)",
        account_type=AccountType.INCOME,
        account_number="3100",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(income_account)

    # Create expense account for categorization
    expense_account = Account(
        name="Sonstiges (Other)",
        account_type=AccountType.EXPENSE,
        account_number="4900",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(expense_account)

    await integration_session.commit()

    return {
        "opening_balance": opening_balance_account,
        "income": income_account,
        "expense": expense_account,
    }


@pytest_asyncio.fixture
async def setup_asset_account_and_mapping(integration_session, setup_chart_of_accounts):
    """Set up asset account and mapping for the test IBAN."""
    account_repo = AccountRepositorySQLAlchemy(integration_session, TEST_USER_CONTEXT)
    mapping_repo = AccountMappingRepositorySQLAlchemy(
        integration_session, TEST_USER_CONTEXT,
    )

    # Create asset account for bank account
    asset_account = Account(
        name="DKB Checking",
        account_type=AccountType.ASSET,
        account_number=IBAN,  # Asset accounts use IBAN as account number
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )
    await account_repo.save(asset_account)

    # Create account mapping
    mapping = AccountMapping(
        iban=IBAN,
        accounting_account_id=asset_account.id,
        account_name="DKB Checking",
        is_active=True,
        user_id=TEST_USER_ID,
    )
    await mapping_repo.save(mapping)

    await integration_session.commit()

    return {
        "asset_account": asset_account,
        "mapping": mapping,
        **setup_chart_of_accounts,
    }


# ============================================================================
# Integration Tests
# ============================================================================


class TestOpeningBalanceE2E:
    """End-to-end integration tests for opening balance."""

    @pytest.mark.asyncio
    async def test_first_sync_creates_opening_balance_in_database(
        self,
        integration_session,
        setup_asset_account_and_mapping,
    ):
        """
        E2E test: First sync should create and persist opening balance.

        This tests the complete flow from sync command to database.
        """
        # Arrange - repositories
        account_repo = AccountRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        transaction_repo = TransactionRepositorySQLAlchemy(
            integration_session,
            account_repo,
            TEST_USER_CONTEXT,
        )
        mapping_repo = AccountMappingRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        import_repo = TransactionImportRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        bank_transaction_repo = BankTransactionRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        bank_account_repo = BankAccountRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )

        # Mock bank adapter
        adapter = AsyncMock()
        adapter.is_connected = Mock(return_value=False)
        adapter.set_tan_callback = AsyncMock()
        adapter.connect = AsyncMock()
        adapter.disconnect = AsyncMock()

        bank_transactions = _make_bank_transactions()
        adapter.fetch_transactions.return_value = bank_transactions
        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("1000.00")),
        ]

        # Create counter-account resolution service (returns default accounts)
        counter_account_resolution_service = AsyncMock(
            spec=CounterAccountResolutionService,
        )
        # Return a ResolutionResult with no account (will fall back to default)
        counter_account_resolution_service.resolve_counter_account_with_details.return_value = ResolutionResult(
            account=None,
            ai_result=None,
            source=None,
        )

        # Configure fallback account resolution
        async def mock_get_fallback(is_expense: bool, account_repository):
            if is_expense:
                return setup_asset_account_and_mapping["expense"]
            return setup_asset_account_and_mapping["income"]

        counter_account_resolution_service.get_fallback_account.side_effect = mock_get_fallback

        # Create import service
        bank_account_import_service = BankAccountImportService(
            account_repository=account_repo,
            mapping_repository=mapping_repo,
            current_user=TEST_USER_CONTEXT,
        )

        import_service = _create_import_service(
            bank_account_import_service=bank_account_import_service,
            counter_account_resolution_service=counter_account_resolution_service,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            mapping_repo=mapping_repo,
            import_repo=import_repo,
        )

        # Create sync command with all repos
        command = TransactionSyncCommand(
            bank_adapter=adapter,
            import_service=import_service,
            mapping_repo=mapping_repo,
            import_repo=import_repo,
            current_user=TEST_USER_CONTEXT,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            bank_account_repo=bank_account_repo,
            bank_transaction_repo=bank_transaction_repo,
        )

        # Act - execute sync
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        # Commit changes
        await integration_session.commit()

        # Assert - sync succeeded
        assert result.success is True

        # Assert - opening balance was created and persisted
        opening_balance_txns = await transaction_repo.find_by_metadata(
            metadata_key=OPENING_BALANCE_IBAN_KEY,
            metadata_value=IBAN,
        )
        assert len(opening_balance_txns) == 1

        opening_balance_txn = opening_balance_txns[0]
        assert opening_balance_txn.is_posted is True
        assert opening_balance_txn.has_metadata_raw(OPENING_BALANCE_METADATA_KEY)
        assert opening_balance_txn.get_metadata_raw(OPENING_BALANCE_METADATA_KEY) is True

        # Verify the opening balance amount:
        # current_balance = 1000
        # net_change = +500 - 100 - 50 = +350
        # opening_balance = 1000 - 350 = 650
        entries = opening_balance_txn.entries
        debit_entry = next(e for e in entries if e.is_debit())
        assert debit_entry.debit.amount == Decimal("650.00")

        # Verify date is earliest transaction date (Jan 10)
        assert opening_balance_txn.date.date() == date(2025, 1, 10)

        # Verify description
        assert "Opening Balance" in opening_balance_txn.description

    @pytest.mark.asyncio
    async def test_second_sync_does_not_create_duplicate_opening_balance(
        self,
        integration_session,
        setup_asset_account_and_mapping,
    ):
        """
        E2E test: Second sync should not create duplicate opening balance.

        Tests idempotency with real database.
        """
        # Arrange
        account_repo = AccountRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        transaction_repo = TransactionRepositorySQLAlchemy(
            integration_session,
            account_repo,
            TEST_USER_CONTEXT,
        )
        mapping_repo = AccountMappingRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        import_repo = TransactionImportRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        bank_transaction_repo = BankTransactionRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        bank_account_repo = BankAccountRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )

        adapter = AsyncMock()
        adapter.is_connected = Mock(return_value=False)
        adapter.set_tan_callback = AsyncMock()
        adapter.connect = AsyncMock()
        adapter.disconnect = AsyncMock()

        bank_transactions = _make_bank_transactions()
        adapter.fetch_transactions.return_value = bank_transactions
        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("1000.00")),
        ]

        counter_account_resolution_service = AsyncMock(
            spec=CounterAccountResolutionService,
        )
        counter_account_resolution_service.resolve_counter_account_with_details.return_value = ResolutionResult(
            account=None,
            ai_result=None,
            source=None,
        )

        # Configure fallback account resolution
        async def mock_get_fallback(is_expense: bool, account_repository):
            if is_expense:
                return setup_asset_account_and_mapping["expense"]
            return setup_asset_account_and_mapping["income"]

        counter_account_resolution_service.get_fallback_account.side_effect = mock_get_fallback

        bank_account_import_service = BankAccountImportService(
            account_repository=account_repo,
            mapping_repository=mapping_repo,
            current_user=TEST_USER_CONTEXT,
        )

        import_service = _create_import_service(
            bank_account_import_service=bank_account_import_service,
            counter_account_resolution_service=counter_account_resolution_service,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            mapping_repo=mapping_repo,
            import_repo=import_repo,
        )

        command = TransactionSyncCommand(
            bank_adapter=adapter,
            import_service=import_service,
            mapping_repo=mapping_repo,
            import_repo=import_repo,
            current_user=TEST_USER_CONTEXT,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            bank_account_repo=bank_account_repo,
            bank_transaction_repo=bank_transaction_repo,
        )

        # Act - First sync
        result1 = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        await integration_session.commit()

        # Verify first sync created opening balance
        assert result1.success is True
        opening_balance_after_first = await transaction_repo.find_by_metadata(
            metadata_key=OPENING_BALANCE_IBAN_KEY,
            metadata_value=IBAN,
        )
        assert len(opening_balance_after_first) == 1

        # Act - Second sync (simulating next day)
        adapter.fetch_transactions.return_value = [
            BankTransaction(
                booking_date=date(2025, 2, 1),
                value_date=date(2025, 2, 1),
                amount=Decimal("-25.00"),
                currency="EUR",
                purpose="New transaction",
            ),
        ]

        result2 = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 28),
        )
        await integration_session.commit()

        # Assert - Second sync succeeded but no new opening balance
        assert result2.success is True

        opening_balance_after_second = await transaction_repo.find_by_metadata(
            metadata_key=OPENING_BALANCE_IBAN_KEY,
            metadata_value=IBAN,
        )
        # Should still be exactly 1 (no duplicate)
        assert len(opening_balance_after_second) == 1

        # Should be the same transaction
        assert opening_balance_after_first[0].id == opening_balance_after_second[0].id

    @pytest.mark.asyncio
    async def test_opening_balance_with_negative_balance(
        self,
        integration_session,
        setup_asset_account_and_mapping,
    ):
        """
        E2E test: Opening balance should handle overdraft (negative balance).
        """
        # Arrange
        account_repo = AccountRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        transaction_repo = TransactionRepositorySQLAlchemy(
            integration_session,
            account_repo,
            TEST_USER_CONTEXT,
        )
        mapping_repo = AccountMappingRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        import_repo = TransactionImportRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        bank_transaction_repo = BankTransactionRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        bank_account_repo = BankAccountRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )

        adapter = AsyncMock()
        adapter.is_connected = Mock(return_value=False)
        adapter.set_tan_callback = AsyncMock()
        adapter.connect = AsyncMock()
        adapter.disconnect = AsyncMock()

        # Only income transaction
        bank_transactions = [
            BankTransaction(
                booking_date=date(2025, 1, 15),
                value_date=date(2025, 1, 15),
                amount=Decimal("1000.00"),  # Big income
                currency="EUR",
                purpose="Large payment",
            ),
        ]
        adapter.fetch_transactions.return_value = bank_transactions

        # Current balance is 500, received 1000 → opening was -500 (overdraft)
        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("500.00")),
        ]

        counter_account_resolution_service = AsyncMock(
            spec=CounterAccountResolutionService,
        )
        counter_account_resolution_service.resolve_counter_account_with_details.return_value = ResolutionResult(
            account=None,
            ai_result=None,
            source=None,
        )

        # Configure fallback account resolution
        async def mock_get_fallback(is_expense: bool, account_repository):
            if is_expense:
                return setup_asset_account_and_mapping["expense"]
            return setup_asset_account_and_mapping["income"]

        counter_account_resolution_service.get_fallback_account.side_effect = mock_get_fallback

        bank_account_import_service = BankAccountImportService(
            account_repository=account_repo,
            mapping_repository=mapping_repo,
            current_user=TEST_USER_CONTEXT,
        )

        import_service = _create_import_service(
            bank_account_import_service=bank_account_import_service,
            counter_account_resolution_service=counter_account_resolution_service,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            mapping_repo=mapping_repo,
            import_repo=import_repo,
        )

        command = TransactionSyncCommand(
            bank_adapter=adapter,
            import_service=import_service,
            mapping_repo=mapping_repo,
            import_repo=import_repo,
            current_user=TEST_USER_CONTEXT,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            bank_account_repo=bank_account_repo,
            bank_transaction_repo=bank_transaction_repo,
        )

        # Act
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        await integration_session.commit()

        # Assert
        assert result.success is True

        opening_balance_txns = await transaction_repo.find_by_metadata(
            metadata_key=OPENING_BALANCE_IBAN_KEY,
            metadata_value=IBAN,
        )
        assert len(opening_balance_txns) == 1

        opening_balance_txn = opening_balance_txns[0]

        # Verify the negative opening balance:
        # current = 500, income = 1000, opening = 500 - 1000 = -500
        # For negative: Credit Asset, Debit Equity
        entries = opening_balance_txn.entries
        credit_entry = next(e for e in entries if not e.is_debit())

        # Asset account should be credited (for overdraft)
        assert credit_entry.account.account_type == AccountType.ASSET
        assert credit_entry.credit.amount == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_opening_balance_persists_across_sessions(
        self,
        integration_engine,
        setup_asset_account_and_mapping,
        integration_session,
    ):
        """
        E2E test: Opening balance should persist and be retrievable in new session.
        """
        # This test verifies data actually persists, not just in-memory

        # Arrange - use first session to create opening balance
        account_repo = AccountRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        transaction_repo = TransactionRepositorySQLAlchemy(
            integration_session,
            account_repo,
            TEST_USER_CONTEXT,
        )
        mapping_repo = AccountMappingRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        import_repo = TransactionImportRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        bank_transaction_repo = BankTransactionRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )
        bank_account_repo = BankAccountRepositorySQLAlchemy(
            integration_session, TEST_USER_CONTEXT,
        )

        adapter = AsyncMock()
        adapter.is_connected = Mock(return_value=False)
        adapter.set_tan_callback = AsyncMock()
        adapter.connect = AsyncMock()
        adapter.disconnect = AsyncMock()
        adapter.fetch_transactions.return_value = _make_bank_transactions()
        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("1000.00")),
        ]

        counter_account_resolution_service = AsyncMock(
            spec=CounterAccountResolutionService,
        )
        counter_account_resolution_service.resolve_counter_account_with_details.return_value = ResolutionResult(
            account=None,
            ai_result=None,
            source=None,
        )

        # Configure fallback account resolution
        async def mock_get_fallback(is_expense: bool, account_repository):
            if is_expense:
                return setup_asset_account_and_mapping["expense"]
            return setup_asset_account_and_mapping["income"]

        counter_account_resolution_service.get_fallback_account.side_effect = mock_get_fallback

        bank_account_import_service = BankAccountImportService(
            account_repository=account_repo,
            mapping_repository=mapping_repo,
            current_user=TEST_USER_CONTEXT,
        )

        import_service = _create_import_service(
            bank_account_import_service=bank_account_import_service,
            counter_account_resolution_service=counter_account_resolution_service,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            mapping_repo=mapping_repo,
            import_repo=import_repo,
        )

        command = TransactionSyncCommand(
            bank_adapter=adapter,
            import_service=import_service,
            mapping_repo=mapping_repo,
            import_repo=import_repo,
            current_user=TEST_USER_CONTEXT,
            account_repo=account_repo,
            transaction_repo=transaction_repo,
            bank_account_repo=bank_account_repo,
            bank_transaction_repo=bank_transaction_repo,
        )

        # Act - Create opening balance
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        await integration_session.commit()
        assert result.success is True

        # Get the opening balance ID
        opening_balance_txns = await transaction_repo.find_by_metadata(
            metadata_key=OPENING_BALANCE_IBAN_KEY,
            metadata_value=IBAN,
        )
        opening_balance_id = opening_balance_txns[0].id

        # Create a NEW session to verify persistence
        async_session_maker = async_sessionmaker(
            integration_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with async_session_maker() as new_session:
            new_account_repo = AccountRepositorySQLAlchemy(
                new_session, TEST_USER_CONTEXT,
            )
            new_transaction_repo = TransactionRepositorySQLAlchemy(
                new_session,
                new_account_repo,
                TEST_USER_CONTEXT,
            )

            # Assert - should be able to retrieve in new session
            retrieved = await new_transaction_repo.find_by_id(opening_balance_id)
            assert retrieved is not None
            assert retrieved.has_metadata_raw(OPENING_BALANCE_METADATA_KEY)
            assert retrieved.get_metadata_raw(OPENING_BALANCE_IBAN_KEY) == IBAN
