"""Unit tests for opening balance creation in TransactionSyncCommand."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from swen.application.commands.integration import TransactionSyncCommand
from swen.application.ports.identity import CurrentUser
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.services import (
    OPENING_BALANCE_IBAN_KEY,
    OPENING_BALANCE_METADATA_KEY,
)
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankCredentials, BankTransaction
from swen.domain.integration.entities import AccountMapping
from swen.domain.integration.value_objects import ImportStatus
from swen.domain.shared.value_objects.secure_string import SecureString

IBAN = "DE89370400440532013000"
BLZ = "37040044"
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def _make_credentials() -> BankCredentials:
    return BankCredentials(
        blz=BLZ,
        username=SecureString("user"),
        pin=SecureString("123456"),
        endpoint="https://fints.example.com/fints",
    )


def _make_mapping(
    accounting_account_id: UUID | None = None,
    active: bool = True,
) -> AccountMapping:
    return AccountMapping(
        iban=IBAN,
        accounting_account_id=accounting_account_id or uuid4(),
        account_name="Test Account",
        user_id=TEST_USER_ID,
        is_active=active,
    )


def _make_asset_account() -> Account:
    """Create asset account matching the IBAN (stored separately on Account)."""
    return Account(
        name="DKB Checking",
        account_type=AccountType.ASSET,
        account_number="0532013000",  # display code (local account number)
        user_id=TEST_USER_ID,
        iban=IBAN,
        default_currency=Currency("EUR"),
    )


def _make_equity_account() -> Account:
    """Create opening balance equity account."""
    return Account(
        name="Anfangssaldo (Opening Balance)",
        account_type=AccountType.EQUITY,
        account_number="2000",
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
    )


def _make_bank_account(iban: str, balance: Decimal) -> SimpleNamespace:
    """Create a mock bank account with balance."""
    return SimpleNamespace(
        iban=iban,
        balance=balance,
        currency="EUR",
    )


def _make_bank_transactions() -> list[BankTransaction]:
    """Create sample bank transactions for testing."""
    return [
        BankTransaction(
            booking_date=date(2025, 1, 15),
            value_date=date(2025, 1, 15),
            amount=Decimal("500.00"),  # Income
            currency="EUR",
            purpose="Salary",
        ),
        BankTransaction(
            booking_date=date(2025, 1, 20),
            value_date=date(2025, 1, 20),
            amount=Decimal("-100.00"),  # Expense
            currency="EUR",
            purpose="Groceries",
        ),
        BankTransaction(
            booking_date=date(2025, 1, 10),  # Earliest
            value_date=date(2025, 1, 10),
            amount=Decimal("-50.00"),
            currency="EUR",
            purpose="Coffee",
        ),
    ]


def _make_stored_transaction(tx, is_new: bool = True):
    """Create a mock StoredBankTransaction for testing."""
    from uuid import uuid4

    return SimpleNamespace(
        id=uuid4(),
        identity_hash="test_hash",
        hash_sequence=1,
        transaction=tx,
        is_imported=False,
        is_new=is_new,
    )


def _make_command_with_repos():
    """Create command with all repositories including account and transaction repos."""
    adapter = AsyncMock()
    adapter.is_connected = Mock(return_value=False)
    adapter.set_tan_callback = AsyncMock()
    adapter.connect = AsyncMock()
    adapter.fetch_transactions = AsyncMock()
    adapter.fetch_accounts = AsyncMock()
    adapter.disconnect = AsyncMock()

    import_service = AsyncMock()
    mapping_repo = AsyncMock()
    import_repo = AsyncMock()
    account_repo = AsyncMock()
    transaction_repo = AsyncMock()
    bank_transaction_repo = AsyncMock()

    # Default: stored transactions are returned as new
    bank_transaction_repo.save_batch_with_deduplication.return_value = []

    # Create user context
    current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

    command = TransactionSyncCommand(
        bank_adapter=adapter,
        import_service=import_service,
        mapping_repo=mapping_repo,
        import_repo=import_repo,
        current_user=current_user,
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        bank_transaction_repo=bank_transaction_repo,
    )

    return (
        command,
        adapter,
        import_service,
        mapping_repo,
        import_repo,
        account_repo,
        transaction_repo,
        bank_transaction_repo,
    )


class TestOpeningBalanceCreation:
    """Tests for opening balance creation during first sync."""

    @pytest.mark.asyncio
    async def test_creates_opening_balance_on_first_sync(self):
        """Should create opening balance when syncing for the first time."""
        (
            command,
            adapter,
            import_service,
            mapping_repo,
            import_repo,
            account_repo,
            transaction_repo,
            bank_transaction_repo,
        ) = _make_command_with_repos()

        # Setup
        asset_account = _make_asset_account()
        mapping_repo.find_by_iban.return_value = _make_mapping(
            accounting_account_id=asset_account.id,
        )
        import_repo.find_by_iban.return_value = []  # No previous imports

        bank_transactions = _make_bank_transactions()
        adapter.fetch_transactions.return_value = bank_transactions
        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("1000.00")),
        ]

        # Bank transaction repo returns all as new
        stored_txs = [
            _make_stored_transaction(tx, is_new=True) for tx in bank_transactions
        ]
        bank_transaction_repo.save_batch_with_deduplication.return_value = stored_txs

        # No existing opening balance
        transaction_repo.find_by_metadata.return_value = []

        equity_account = _make_equity_account()
        account_repo.find_by_id.return_value = asset_account
        account_repo.find_by_account_number.return_value = equity_account

        import_service.import_from_stored_transactions.return_value = [
            SimpleNamespace(status=ImportStatus.SUCCESS) for _ in bank_transactions
        ]

        # Execute
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            # user_id is now obtained from CurrentUser in constructor
        )

        # Verify
        assert result.success is True

        # Should have saved opening balance transaction
        transaction_repo.save.assert_called_once()
        saved_txn = transaction_repo.save.call_args.args[0]

        # Verify the opening balance transaction
        assert saved_txn.is_posted is True
        assert saved_txn.has_metadata_raw(OPENING_BALANCE_METADATA_KEY)
        assert saved_txn.get_metadata_raw(OPENING_BALANCE_IBAN_KEY) == IBAN

        # Verify opening balance amount calculation:
        # current_balance = 1000
        # net_change = +500 - 100 - 50 = +350
        # opening_balance = 1000 - 350 = 650
        entries = saved_txn.entries
        debit_entry = next(e for e in entries if e.is_debit())
        assert debit_entry.debit.amount == Decimal("650.00")

        # Verify date is earliest transaction date (Jan 10)
        assert saved_txn.date.date() == date(2025, 1, 10)

    @pytest.mark.asyncio
    async def test_skips_opening_balance_when_already_exists(self):
        """Should not create duplicate opening balance."""
        (
            command,
            adapter,
            import_service,
            mapping_repo,
            import_repo,
            _account_repo,
            transaction_repo,
            bank_transaction_repo,
        ) = _make_command_with_repos()

        # Setup
        asset_account = _make_asset_account()
        mapping_repo.find_by_iban.return_value = _make_mapping(
            accounting_account_id=asset_account.id,
        )
        import_repo.find_by_iban.return_value = []

        bank_transactions = _make_bank_transactions()
        adapter.fetch_transactions.return_value = bank_transactions
        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("1000.00")),
        ]

        # Bank transaction repo returns all as new
        stored_txs = [
            _make_stored_transaction(tx, is_new=True) for tx in bank_transactions
        ]
        bank_transaction_repo.save_batch_with_deduplication.return_value = stored_txs

        # Opening balance ALREADY EXISTS
        existing_opening_balance = SimpleNamespace(id=uuid4())
        transaction_repo.find_by_metadata.return_value = [existing_opening_balance]

        import_service.import_from_stored_transactions.return_value = [
            SimpleNamespace(status=ImportStatus.SUCCESS) for _ in bank_transactions
        ]

        # Execute
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            # user_id is now obtained from CurrentUser in constructor
        )

        # Verify - should NOT save new opening balance
        assert result.success is True
        transaction_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_fails_without_bank_transaction_repo(self):
        """Should fail when bank_transaction_repo is not provided."""
        adapter = AsyncMock()
        adapter.is_connected = Mock(return_value=False)
        adapter.set_tan_callback = AsyncMock()
        adapter.connect = AsyncMock()
        adapter.fetch_transactions = AsyncMock()
        adapter.disconnect = AsyncMock()

        import_service = AsyncMock()
        mapping_repo = AsyncMock()
        import_repo = AsyncMock()
        current_user = CurrentUser(user_id=TEST_USER_ID, email="test@example.com")

        # NO bank_transaction_repo - should cause failure
        command = TransactionSyncCommand(
            bank_adapter=adapter,
            import_service=import_service,
            mapping_repo=mapping_repo,
            import_repo=import_repo,
            current_user=current_user,
        )

        mapping_repo.find_by_iban.return_value = _make_mapping()
        import_repo.find_by_iban.return_value = []

        bank_transactions = _make_bank_transactions()
        adapter.fetch_transactions.return_value = bank_transactions

        # Execute - should fail because bank_transaction_repo is required
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )

        assert result.success is False
        assert result.error_message is not None
        assert "bank_transaction_repo is required" in result.error_message

    @pytest.mark.asyncio
    async def test_skips_opening_balance_without_transactions(self):
        """Should skip opening balance when no transactions to import."""
        (
            command,
            adapter,
            import_service,
            mapping_repo,
            import_repo,
            _account_repo,
            transaction_repo,
            bank_transaction_repo,
        ) = _make_command_with_repos()

        mapping_repo.find_by_iban.return_value = _make_mapping()
        import_repo.find_by_iban.return_value = []

        # NO transactions
        adapter.fetch_transactions.return_value = []
        bank_transaction_repo.save_batch_with_deduplication.return_value = []
        import_service.import_from_stored_transactions.return_value = []

        # Execute
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            # user_id is now obtained from CurrentUser in constructor
        )

        assert result.success is True
        # Should not try to create opening balance
        transaction_repo.find_by_metadata.assert_not_called()
        transaction_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_opening_balance_without_current_balance(self):
        """Should skip opening balance when current balance not available."""
        (
            command,
            adapter,
            import_service,
            mapping_repo,
            import_repo,
            _account_repo,
            transaction_repo,
            bank_transaction_repo,
        ) = _make_command_with_repos()

        mapping_repo.find_by_iban.return_value = _make_mapping()
        import_repo.find_by_iban.return_value = []

        bank_transactions = _make_bank_transactions()
        adapter.fetch_transactions.return_value = bank_transactions

        # Bank transaction repo returns all as new
        stored_txs = [
            _make_stored_transaction(tx, is_new=True) for tx in bank_transactions
        ]
        bank_transaction_repo.save_batch_with_deduplication.return_value = stored_txs

        # Account has NO balance
        adapter.fetch_accounts.return_value = [
            SimpleNamespace(iban=IBAN, balance=None, currency="EUR"),
        ]

        transaction_repo.find_by_metadata.return_value = []

        import_service.import_from_stored_transactions.return_value = [
            SimpleNamespace(status=ImportStatus.SUCCESS) for _ in bank_transactions
        ]

        # Execute
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            # user_id is now obtained from CurrentUser in constructor
        )

        assert result.success is True
        # Should not save opening balance (balance not available)
        transaction_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_negative_opening_balance(self):
        """Should correctly handle negative opening balance (overdraft)."""
        (
            command,
            adapter,
            import_service,
            mapping_repo,
            import_repo,
            account_repo,
            transaction_repo,
            bank_transaction_repo,
        ) = _make_command_with_repos()

        asset_account = _make_asset_account()
        mapping_repo.find_by_iban.return_value = _make_mapping(
            accounting_account_id=asset_account.id,
        )
        import_repo.find_by_iban.return_value = []

        # Only income transaction
        bank_transactions = [
            BankTransaction(
                booking_date=date(2025, 1, 15),
                value_date=date(2025, 1, 15),
                amount=Decimal("1000.00"),  # Large income
                currency="EUR",
                purpose="Big payment",
            ),
        ]
        adapter.fetch_transactions.return_value = bank_transactions

        # Bank transaction repo returns all as new
        stored_txs = [
            _make_stored_transaction(tx, is_new=True) for tx in bank_transactions
        ]
        bank_transaction_repo.save_batch_with_deduplication.return_value = stored_txs

        # Current balance is 500, but we received 1000
        # Opening balance = 500 - 1000 = -500 (was in overdraft)
        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("500.00")),
        ]

        transaction_repo.find_by_metadata.return_value = []

        equity_account = _make_equity_account()
        account_repo.find_by_id.return_value = asset_account
        account_repo.find_by_account_number.return_value = equity_account

        import_service.import_from_stored_transactions.return_value = [
            SimpleNamespace(status=ImportStatus.SUCCESS),
        ]

        # Execute
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            # user_id is now obtained from CurrentUser in constructor
        )

        assert result.success is True
        transaction_repo.save.assert_called_once()

        saved_txn = transaction_repo.save.call_args.args[0]
        entries = saved_txn.entries

        # For negative balance: Credit Asset, Debit Equity
        credit_entry = next(e for e in entries if not e.is_debit())
        assert credit_entry.account == asset_account
        assert credit_entry.credit.amount == Decimal("500.00")

    @pytest.mark.asyncio
    async def test_opening_balance_does_not_block_sync_on_error(self):
        """Should continue sync even if opening balance creation fails."""
        (
            command,
            adapter,
            import_service,
            mapping_repo,
            import_repo,
            account_repo,
            transaction_repo,
            bank_transaction_repo,
        ) = _make_command_with_repos()

        mapping_repo.find_by_iban.return_value = _make_mapping(
            accounting_account_id=uuid4(),
        )
        import_repo.find_by_iban.return_value = []

        bank_transactions = _make_bank_transactions()
        adapter.fetch_transactions.return_value = bank_transactions

        # Bank transaction repo returns all as new
        stored_txs = [
            _make_stored_transaction(tx, is_new=True) for tx in bank_transactions
        ]
        bank_transaction_repo.save_batch_with_deduplication.return_value = stored_txs

        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("1000.00")),
        ]

        transaction_repo.find_by_metadata.return_value = []

        # Mapped asset account not found - should fail opening balance but continue sync
        account_repo.find_by_id.return_value = None

        import_service.import_from_stored_transactions.return_value = [
            SimpleNamespace(status=ImportStatus.SUCCESS) for _ in bank_transactions
        ]

        # Execute - should succeed despite opening balance failure
        result = await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            # user_id is now obtained from CurrentUser in constructor
        )

        assert result.success is True
        assert result.transactions_imported == 3

        # Opening balance save should not have been called
        transaction_repo.save.assert_not_called()


class TestOpeningBalanceIdempotency:
    """Tests for idempotency of opening balance creation."""

    @pytest.mark.asyncio
    async def test_find_by_metadata_called_with_correct_params(self):
        """Should check for existing opening balance with correct IBAN."""
        (
            command,
            adapter,
            import_service,
            mapping_repo,
            import_repo,
            account_repo,
            transaction_repo,
            bank_transaction_repo,
        ) = _make_command_with_repos()

        asset_account = _make_asset_account()
        mapping_repo.find_by_iban.return_value = _make_mapping(
            accounting_account_id=asset_account.id,
        )
        import_repo.find_by_iban.return_value = []

        bank_transactions = _make_bank_transactions()
        adapter.fetch_transactions.return_value = bank_transactions

        # Bank transaction repo returns all as new
        stored_txs = [
            _make_stored_transaction(tx, is_new=True) for tx in bank_transactions
        ]
        bank_transaction_repo.save_batch_with_deduplication.return_value = stored_txs

        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("1000.00")),
        ]

        # Return empty to indicate no existing opening balance
        transaction_repo.find_by_metadata.return_value = []

        equity_account = _make_equity_account()
        account_repo.find_by_id.return_value = asset_account
        account_repo.find_by_account_number.return_value = equity_account

        import_service.import_from_stored_transactions.return_value = [
            SimpleNamespace(status=ImportStatus.SUCCESS) for _ in bank_transactions
        ]

        await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            # user_id is now obtained from CurrentUser in constructor
        )

        # Verify find_by_metadata was called with correct parameters
        transaction_repo.find_by_metadata.assert_called_once_with(
            metadata_key=OPENING_BALANCE_IBAN_KEY,
            metadata_value=IBAN,
        )

    @pytest.mark.asyncio
    async def test_multiple_syncs_only_create_one_opening_balance(self):
        """Simulates multiple syncs - only first should create opening balance."""
        (
            command,
            adapter,
            import_service,
            mapping_repo,
            import_repo,
            account_repo,
            transaction_repo,
            bank_transaction_repo,
        ) = _make_command_with_repos()

        asset_account = _make_asset_account()
        mapping_repo.find_by_iban.return_value = _make_mapping(
            accounting_account_id=asset_account.id,
        )
        import_repo.find_by_iban.return_value = []

        bank_transactions = _make_bank_transactions()
        adapter.fetch_transactions.return_value = bank_transactions

        # Bank transaction repo returns all as new
        stored_txs = [
            _make_stored_transaction(tx, is_new=True) for tx in bank_transactions
        ]
        bank_transaction_repo.save_batch_with_deduplication.return_value = stored_txs

        adapter.fetch_accounts.return_value = [
            _make_bank_account(IBAN, Decimal("1000.00")),
        ]

        equity_account = _make_equity_account()
        account_repo.find_by_id.return_value = asset_account
        account_repo.find_by_account_number.return_value = equity_account

        import_service.import_from_stored_transactions.return_value = [
            SimpleNamespace(status=ImportStatus.SUCCESS) for _ in bank_transactions
        ]

        # First sync - no existing opening balance
        transaction_repo.find_by_metadata.return_value = []

        await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            # user_id is now obtained from CurrentUser in constructor
        )

        # Opening balance should have been saved
        assert transaction_repo.save.call_count == 1
        first_call_txn = transaction_repo.save.call_args.args[0]

        # Second sync - opening balance now exists
        transaction_repo.find_by_metadata.return_value = [first_call_txn]
        transaction_repo.save.reset_mock()

        await command.execute(
            iban=IBAN,
            credentials=_make_credentials(),
            start_date=date(2025, 2, 1),
            end_date=date(2025, 2, 28),
            # user_id is now obtained from CurrentUser in constructor
        )

        # Should NOT save another opening balance
        transaction_repo.save.assert_not_called()
