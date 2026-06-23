"""Property-based integration tests for save_complete_import atomicity.

**Validates: Requirements 5.1, 5.6, Property 1, Property 10**

Atomicity invariant: for any (amount, ob_adjustment_amount, inject_fault) triplet,
when save_complete_import raises (due to injected fault), no Transaction, no
transitioned TransactionImportRecord, and no opening-balance adjustment are
observable in the database for that failed item.

These tests require RUN_INTEGRATION=1 and a real Postgres DB (via Testcontainers).
They are skipped automatically when RUN_INTEGRATION is not set.
"""

from __future__ import annotations

import asyncio
import itertools
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

# Unique counter so that each Hypothesis example uses distinct account numbers
# (the DB tables are not wiped between examples within one test run).
_example_counter = itertools.count(1)

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
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
# Module-level marker: only run when RUN_INTEGRATION=1
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.integration

_IBAN = "DE89370400440532013000"
_BLZ = "37040044"


# ---------------------------------------------------------------------------
# Domain object helpers
# ---------------------------------------------------------------------------


def _current_user() -> CurrentUser:
    return CurrentUser(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)


def _make_asset_account(account_number: str = "1200", iban: str = _IBAN) -> Account:
    return Account(
        name="DKB Girokonto",
        account_type=AccountType.ASSET,
        account_number=account_number,
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
        iban=iban,
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
    counter_account: Account,
    amount: Decimal = Decimal("100.00"),
) -> Transaction:
    txn = Transaction(
        description="PBT import transaction",
        user_id=TEST_USER_ID,
        date=datetime(2024, 6, 10, tzinfo=timezone.utc),
        source=TransactionSource.BANK_IMPORT,
        source_iban=_IBAN,
    )
    money = Money(amount=amount)
    txn.add_debit(asset_account, money)
    txn.add_credit(counter_account, money)
    txn.post()
    return txn


def _make_import_record(bank_tx_id: object) -> TransactionImport:
    return TransactionImport(
        user_id=TEST_USER_ID,
        bank_transaction_id=bank_tx_id,  # type: ignore[arg-type]
        booking_date=date(2024, 6, 10),
        status=ImportStatus.PENDING,
    )


def _make_bank_account(iban: str = _IBAN) -> BankAccount:
    return BankAccount(
        iban=iban,
        account_number="532013000",
        blz=_BLZ,
        account_holder="Test User",
        account_type="Girokonto",
        currency="EUR",
        balance=Decimal("1000.00"),
    )


def _make_bank_transaction(amount: Decimal, iban: str = _IBAN) -> BankTransaction:
    return BankTransaction(
        booking_date=date(2024, 6, 10),
        value_date=date(2024, 6, 10),
        amount=amount,
        currency="EUR",
        purpose="PBT test transaction",
    )


# ---------------------------------------------------------------------------
# DB setup helpers
# ---------------------------------------------------------------------------


async def _setup_accounts(
    session: AsyncSession,
    n: int = 0,
) -> tuple[Account, Account, Account, str]:
    """Persist asset, income, and equity accounts; return them.

    ``n`` is used as a suffix so that successive Hypothesis examples do not
    collide on the unique (user_id, account_number) or IBAN constraints.
    """
    iban = f"DE{89370400440532013000 + n:020d}"[:22]
    current_user = _current_user()
    account_repo = AccountRepositorySQLAlchemy(session, current_user)

    asset = _make_asset_account(account_number=f"{1200 + n}", iban=iban)
    income = _make_income_account(account_number=f"{3000 + n}")
    equity = _make_equity_account(account_number=f"{2000 + n}")

    await account_repo.save(asset)
    await account_repo.save(income)
    await account_repo.save(equity)

    return asset, income, equity, iban


async def _setup_bank_tx(session: AsyncSession, amount: Decimal, iban: str) -> object:
    """Persist a bank account + bank transaction; return the stored tx id."""
    current_user = _current_user()
    bank_account_repo = BankAccountRepositorySQLAlchemy(session, current_user)
    bank_tx_repo = BankTransactionRepositorySQLAlchemy(session, current_user)

    await bank_account_repo.save(_make_bank_account(iban=iban))
    bank_tx = _make_bank_transaction(amount, iban=iban)
    stored_ids = await bank_tx_repo.save_batch([bank_tx], iban)
    return stored_ids[0]


# ---------------------------------------------------------------------------
# Core async scenario
# ---------------------------------------------------------------------------


async def _run_atomicity_scenario(  # noqa: PLR0915
    async_engine,  # noqa: ANN001
    amount: Decimal,
    ob_amount: Decimal,
    inject_fault: bool,
    n: int = 0,
) -> None:
    """Execute one hypothesis example against the real DB.

    When inject_fault=True: asserts that no partial state is observable after
    save_complete_import raises.
    When inject_fault=False: asserts that all three writes are durable.
    """
    from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
        AccountRepositorySQLAlchemy as AcctRepo,
    )
    from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
        TransactionRepositorySQLAlchemy,
    )

    session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # ── Setup: persist accounts and a bank transaction ──────────────────────
    async with session_maker() as setup_session:
        asset, income, equity, iban = await _setup_accounts(setup_session, n=n)
        bank_tx_id = await _setup_bank_tx(setup_session, amount, iban=iban)
        await setup_session.commit()

    # ── Build domain objects ─────────────────────────────────────────────────
    accounting_tx = _make_accounting_transaction(asset, income, amount)
    ob_adjustment = _make_accounting_transaction(asset, equity, ob_amount)
    import_record = _make_import_record(bank_tx_id)
    import_record.mark_as_imported(accounting_tx.id)

    raised: Optional[Exception] = None

    # ── Attempt save_complete_import ─────────────────────────────────────────
    async with session_maker() as session:
        current_user = _current_user()
        import_repo = TransactionImportRepositorySQLAlchemy(session, current_user)

        if inject_fault:
            # Inject failure: replace _save_no_commit so it raises before any
            # write is committed, simulating a mid-write DB error.
            tx_repo_inner = import_repo._get_transaction_repository()

            async def _failing_save(transaction: Transaction) -> None:
                raise RuntimeError("PBT injected fault during accounting tx save")

            tx_repo_inner._save_no_commit = _failing_save  # type: ignore[method-assign]

        try:
            await import_repo.save_complete_import(
                import_record=import_record,
                accounting_tx=accounting_tx,
                ob_adjustment=ob_adjustment,
            )
        except Exception as exc:
            raised = exc

    # ── Verify ──────────────────────────────────────────────────────────────
    if inject_fault:
        assert raised is not None, (
            "Expected save_complete_import to raise when fault is injected, "
            "but it succeeded"
        )

        async with session_maker() as verify_session:
            current_user = _current_user()
            verify_import_repo = TransactionImportRepositorySQLAlchemy(
                verify_session, current_user
            )
            acct_repo = AcctRepo(verify_session, current_user)
            tx_repo = TransactionRepositorySQLAlchemy(
                verify_session, acct_repo, current_user
            )

            found_import = await verify_import_repo.find_by_id(import_record.id)
            assert found_import is None, (
                f"Import record {import_record.id} should not be persisted "
                "after a failed save_complete_import"
            )

            found_tx = await tx_repo.find_by_id(accounting_tx.id)
            assert found_tx is None, (
                f"Accounting transaction {accounting_tx.id} should not be "
                "persisted after a failed save_complete_import"
            )

            found_ob = await tx_repo.find_by_id(ob_adjustment.id)
            assert found_ob is None, (
                f"OB adjustment {ob_adjustment.id} should not be persisted "
                "after a failed save_complete_import"
            )
    else:
        assert raised is None, (
            f"save_complete_import raised unexpectedly on happy path: {raised}"
        )

        async with session_maker() as verify_session:
            current_user = _current_user()
            verify_import_repo = TransactionImportRepositorySQLAlchemy(
                verify_session, current_user
            )
            acct_repo = AcctRepo(verify_session, current_user)
            tx_repo = TransactionRepositorySQLAlchemy(
                verify_session, acct_repo, current_user
            )

            found_import = await verify_import_repo.find_by_id(import_record.id)
            assert found_import is not None, (
                "Import record should be persisted on happy path"
            )
            assert found_import.status == ImportStatus.SUCCESS

            found_tx = await tx_repo.find_by_id(accounting_tx.id)
            assert found_tx is not None, (
                "Accounting transaction should be persisted on happy path"
            )

            found_ob = await tx_repo.find_by_id(ob_adjustment.id)
            assert found_ob is not None, (
                "OB adjustment should be persisted on happy path"
            )


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_amounts = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("9999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


# ---------------------------------------------------------------------------
# PBT: atomicity on fault injection
# ---------------------------------------------------------------------------


@pytest.mark.integration
@settings(
    max_examples=50,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    amount=_amounts,
    ob_amount=_amounts,
    inject_fault=st.booleans(),
)
def test_save_complete_import_atomicity(
    async_engine,  # noqa: ANN001  — pytest fixture
    integration_tables,  # noqa: ANN001  — pytest fixture (tables + test users)
    amount: Decimal,
    ob_amount: Decimal,
    inject_fault: bool,
) -> None:
    """Property: when inject_fault=True, no partial state is observable after
    save_complete_import raises.

    **Validates: Requirements 5.1, 5.6, Property 1, Property 10**

    Strategy: hypothesis generates (amount, ob_adjustment_amount, inject_fault)
    triplets. When inject_fault=True, the accounting transaction _save_no_commit
    is replaced with a raising stub, simulating a mid-write DB error. The test
    asserts that no Transaction, no transitioned TransactionImportRecord, and no
    opening-balance adjustment are observable in the DB for the failed item.

    When inject_fault=False, the happy path is exercised: all three writes
    (accounting_tx, import_record, ob_adjustment) must be durable on return.

    Requires RUN_INTEGRATION=1 and a running Postgres instance.
    """
    asyncio.get_event_loop().run_until_complete(
        _run_atomicity_scenario(
            async_engine=async_engine,
            amount=amount,
            ob_amount=ob_amount,
            inject_fault=inject_fault,
            n=next(_example_counter),
        )
    )
