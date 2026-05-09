"""Integration tests for TransactionImportRepositorySQLAlchemy atomic methods.

Covers:
- save_complete_import happy path: all three writes (accounting_tx, import_record,
  optional ob_adjustment) are committed atomically.
- save_complete_import partial-write injection: when a write fails mid-way,
  no observable state is left (all-or-nothing).
- mark_reconciled_as_internal_transfer happy path: both writes committed atomically.
- mark_reconciled_as_internal_transfer partial-write injection: no observable state
  on failure.

These tests require RUN_INTEGRATION=1 and a real Postgres DB (via Testcontainers).
They are skipped automatically when RUN_INTEGRATION is not set.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency, Money, TransactionSource
from swen.domain.banking.value_objects import BankAccount, BankTransaction
from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.value_objects import ImportStatus
from swen.domain.shared.current_user import CurrentUser
from swen.infrastructure.persistence.sqlalchemy.repositories import (
    AccountRepositorySQLAlchemy,
    BankAccountRepositorySQLAlchemy,
    BankTransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    TransactionImportRepositorySQLAlchemy,
)
from tests.shared.fixtures.database import TEST_USER_EMAIL, TEST_USER_ID

# ---------------------------------------------------------------------------
# Skip guard: only run when RUN_INTEGRATION=1
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.integration

_IBAN = "DE89370400440532013000"
_BLZ = "37040044"


def _current_user() -> CurrentUser:
    return CurrentUser(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)


# ---------------------------------------------------------------------------
# Domain object factories
# ---------------------------------------------------------------------------


def _make_asset_account(account_number: str = "1200") -> Account:
    return Account(
        name="DKB Girokonto",
        account_type=AccountType.ASSET,
        account_number=account_number,
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
        iban=_IBAN,
    )


def _make_income_account(account_number: str = "3000") -> Account:
    return Account(
        name="Salary",
        account_type=AccountType.INCOME,
        account_number=account_number,
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
    )


def _make_equity_account(account_number: str = "2000") -> Account:
    return Account(
        name="Opening Balance Equity",
        account_type=AccountType.EQUITY,
        account_number=account_number,
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
    )


def _make_accounting_transaction(
    asset_account: Account,
    income_account: Account,
    amount: Decimal = Decimal("100.00"),
) -> Transaction:
    txn = Transaction(
        description="Test import transaction",
        user_id=TEST_USER_ID,
        date=datetime(2024, 6, 10, tzinfo=timezone.utc),
        source=TransactionSource.BANK_IMPORT,
        source_iban=_IBAN,
    )
    money = Money(amount=amount)
    txn.add_debit(asset_account, money)
    txn.add_credit(income_account, money)
    txn.post()
    return txn


def _make_import_record(bank_tx_id: UUID) -> TransactionImport:
    return TransactionImport(
        user_id=TEST_USER_ID,
        bank_transaction_id=bank_tx_id,
        status=ImportStatus.PENDING,
    )


def _make_bank_account() -> BankAccount:
    return BankAccount(
        iban=_IBAN,
        account_number="532013000",
        blz=_BLZ,
        account_holder="Test User",
        account_type="Girokonto",
        currency="EUR",
        balance=Decimal("1000.00"),
    )


def _make_bank_transaction() -> BankTransaction:
    return BankTransaction(
        booking_date=date(2024, 6, 10),
        value_date=date(2024, 6, 10),
        amount=Decimal("100.00"),
        currency="EUR",
        purpose="Test salary",
    )


# ---------------------------------------------------------------------------
# Helpers to set up accounts in DB
# ---------------------------------------------------------------------------


async def _setup_accounts(
    session: AsyncSession,
) -> tuple[Account, Account, Account]:
    """Create and persist asset, income, and equity accounts."""
    current_user = _current_user()
    account_repo = AccountRepositorySQLAlchemy(session, current_user)

    asset = _make_asset_account()
    income = _make_income_account()
    equity = _make_equity_account()

    await account_repo.save(asset)
    await account_repo.save(income)
    await account_repo.save(equity)

    return asset, income, equity


async def _setup_bank_account_and_transaction(
    session: AsyncSession,
) -> tuple[BankAccount, UUID]:
    """Create and persist a bank account and bank transaction, return stored tx id."""
    current_user = _current_user()
    bank_account_repo = BankAccountRepositorySQLAlchemy(session, current_user)
    bank_tx_repo = BankTransactionRepositorySQLAlchemy(session, current_user)

    bank_account = _make_bank_account()
    await bank_account_repo.save(bank_account)

    bank_tx = _make_bank_transaction()
    stored_ids = await bank_tx_repo.save_batch([bank_tx], _IBAN)
    return bank_account, stored_ids[0]


# ---------------------------------------------------------------------------
# save_complete_import — happy path
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSaveCompleteImportHappyPath:
    """save_complete_import atomically persists all three writes."""

    @pytest.mark.asyncio
    async def test_import_record_persisted(self, db_session):
        """After save_complete_import, the import record is findable."""
        asset, income, _ = await _setup_accounts(db_session)
        _, bank_tx_id = await _setup_bank_account_and_transaction(db_session)

        current_user = _current_user()
        import_repo = TransactionImportRepositorySQLAlchemy(db_session, current_user)

        accounting_tx = _make_accounting_transaction(asset, income)
        import_record = _make_import_record(bank_tx_id)
        import_record.mark_as_imported(accounting_tx.id)

        await import_repo.save_complete_import(
            import_record=import_record,
            accounting_tx=accounting_tx,
        )

        found = await import_repo.find_by_id(import_record.id)
        assert found is not None
        assert found.status == ImportStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_accounting_transaction_persisted(self, db_session):
        """After save_complete_import, the accounting transaction is findable."""
        from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
            AccountRepositorySQLAlchemy,
            TransactionRepositorySQLAlchemy,
        )

        asset, income, _ = await _setup_accounts(db_session)
        _, bank_tx_id = await _setup_bank_account_and_transaction(db_session)

        current_user = _current_user()
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        tx_repo = TransactionRepositorySQLAlchemy(
            db_session, account_repo, current_user
        )
        import_repo = TransactionImportRepositorySQLAlchemy(db_session, current_user)

        accounting_tx = _make_accounting_transaction(asset, income)
        import_record = _make_import_record(bank_tx_id)
        import_record.mark_as_imported(accounting_tx.id)

        await import_repo.save_complete_import(
            import_record=import_record,
            accounting_tx=accounting_tx,
        )

        found_tx = await tx_repo.find_by_id(accounting_tx.id)
        assert found_tx is not None

    @pytest.mark.asyncio
    async def test_ob_adjustment_persisted_when_provided(self, db_session):
        """When ob_adjustment is provided, it is also persisted."""
        from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
            AccountRepositorySQLAlchemy,
            TransactionRepositorySQLAlchemy,
        )

        asset, income, equity = await _setup_accounts(db_session)
        _, bank_tx_id = await _setup_bank_account_and_transaction(db_session)

        current_user = _current_user()
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        tx_repo = TransactionRepositorySQLAlchemy(
            db_session, account_repo, current_user
        )
        import_repo = TransactionImportRepositorySQLAlchemy(db_session, current_user)

        accounting_tx = _make_accounting_transaction(asset, income)
        ob_adjustment = _make_accounting_transaction(asset, equity, Decimal("50.00"))
        import_record = _make_import_record(bank_tx_id)
        import_record.mark_as_imported(accounting_tx.id)

        await import_repo.save_complete_import(
            import_record=import_record,
            accounting_tx=accounting_tx,
            ob_adjustment=ob_adjustment,
        )

        found_ob = await tx_repo.find_by_id(ob_adjustment.id)
        assert found_ob is not None


# ---------------------------------------------------------------------------
# save_complete_import — partial-write injection
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSaveCompleteImportPartialWrite:
    """When save_complete_import raises mid-way, no observable state is left."""

    @pytest.mark.asyncio
    async def test_no_import_record_when_accounting_tx_save_fails(
        self, async_engine, integration_tables
    ):
        """If the accounting transaction save fails, the import record is not persisted."""

        session_maker = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # Set up accounts in a separate session
        async with session_maker() as setup_session:
            asset, income, _ = await _setup_accounts(setup_session)
            _, bank_tx_id = await _setup_bank_account_and_transaction(setup_session)
            await setup_session.commit()

        # Now attempt save_complete_import with a failing accounting tx save
        async with session_maker() as session:
            current_user = _current_user()
            import_repo = TransactionImportRepositorySQLAlchemy(session, current_user)

            accounting_tx = _make_accounting_transaction(asset, income)
            import_record = _make_import_record(bank_tx_id)
            import_record.mark_as_imported(accounting_tx.id)

            # Inject failure: make the transaction repo's _save_no_commit raise
            original_save = import_repo._get_transaction_repository()._save_no_commit

            async def _failing_save(tx):
                raise RuntimeError("Injected failure during accounting tx save")

            import_repo._get_transaction_repository()._save_no_commit = _failing_save  # type: ignore[method-assign]

            with pytest.raises(RuntimeError, match="Injected failure"):
                await import_repo.save_complete_import(
                    import_record=import_record,
                    accounting_tx=accounting_tx,
                )

        # Verify: import record should NOT be in the database
        async with session_maker() as verify_session:
            current_user = _current_user()
            verify_repo = TransactionImportRepositorySQLAlchemy(
                verify_session, current_user
            )
            found = await verify_repo.find_by_id(import_record.id)
            assert found is None, "Import record should not be persisted on failure"


# ---------------------------------------------------------------------------
# mark_reconciled_as_internal_transfer — happy path
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMarkReconciledHappyPath:
    """mark_reconciled_as_internal_transfer atomically persists both writes."""

    @pytest.mark.asyncio
    async def test_import_record_marked_as_success(self, db_session):
        """After mark_reconciled_as_internal_transfer, import record is SUCCESS."""
        from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
            AccountRepositorySQLAlchemy,
            TransactionRepositorySQLAlchemy,
        )

        asset, income, _ = await _setup_accounts(db_session)
        _, bank_tx_id = await _setup_bank_account_and_transaction(db_session)

        current_user = _current_user()
        account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
        tx_repo = TransactionRepositorySQLAlchemy(
            db_session, account_repo, current_user
        )
        import_repo = TransactionImportRepositorySQLAlchemy(db_session, current_user)

        # Create an existing accounting transaction (the one to be reconciled)
        existing_tx = _make_accounting_transaction(asset, income)
        await tx_repo.save(existing_tx)

        # Create a second asset account for the counterparty
        counterparty_asset = Account(
            name="Savings",
            account_type=AccountType.ASSET,
            account_number="1201",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
            iban="DE12500000001234567890",
        )
        await account_repo.save(counterparty_asset)

        import_record = _make_import_record(bank_tx_id)

        await import_repo.mark_reconciled_as_internal_transfer(
            import_record=import_record,
            existing_transaction=existing_tx,
            new_asset_account=counterparty_asset,
            source_iban=_IBAN,
            counterparty_iban="DE12500000001234567890",
        )

        found = await import_repo.find_by_id(import_record.id)
        assert found is not None
        assert found.status == ImportStatus.SUCCESS


# ---------------------------------------------------------------------------
# mark_reconciled_as_internal_transfer — partial-write injection
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMarkReconciledPartialWrite:
    """When mark_reconciled_as_internal_transfer raises, no observable state is left."""

    @pytest.mark.asyncio
    async def test_no_import_record_when_transaction_save_fails(
        self, async_engine, integration_tables
    ):
        """If the transaction save fails, the import record is not persisted."""
        session_maker = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # Set up accounts in a separate session
        async with session_maker() as setup_session:
            asset, income, _ = await _setup_accounts(setup_session)
            _, bank_tx_id = await _setup_bank_account_and_transaction(setup_session)

            from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
                AccountRepositorySQLAlchemy,
                TransactionRepositorySQLAlchemy,
            )

            current_user = _current_user()
            account_repo = AccountRepositorySQLAlchemy(setup_session, current_user)
            tx_repo = TransactionRepositorySQLAlchemy(
                setup_session, account_repo, current_user
            )

            existing_tx = _make_accounting_transaction(asset, income)
            await tx_repo.save(existing_tx)

            counterparty_asset = Account(
                name="Savings",
                account_type=AccountType.ASSET,
                account_number="1202",
                user_id=TEST_USER_ID,
                default_currency=Currency("EUR"),
                iban="DE12500000001234567890",
            )
            await account_repo.save(counterparty_asset)
            await setup_session.commit()

        # Now attempt mark_reconciled with a failing transaction save
        async with session_maker() as session:
            current_user = _current_user()
            import_repo = TransactionImportRepositorySQLAlchemy(session, current_user)

            import_record = _make_import_record(bank_tx_id)

            # Inject failure: make the transaction repo's _save_no_commit raise
            tx_repo_inner = import_repo._get_transaction_repository()

            async def _failing_save(tx):
                raise RuntimeError("Injected failure during transaction save")

            tx_repo_inner._save_no_commit = _failing_save  # type: ignore[method-assign]

            with pytest.raises(RuntimeError, match="Injected failure"):
                await import_repo.mark_reconciled_as_internal_transfer(
                    import_record=import_record,
                    existing_transaction=existing_tx,
                    new_asset_account=counterparty_asset,
                    source_iban=_IBAN,
                    counterparty_iban="DE12500000001234567890",
                )

        # Verify: import record should NOT be in the database
        async with session_maker() as verify_session:
            current_user = _current_user()
            verify_repo = TransactionImportRepositorySQLAlchemy(
                verify_session, current_user
            )
            found = await verify_repo.find_by_id(import_record.id)
            assert found is None, "Import record should not be persisted on failure"
