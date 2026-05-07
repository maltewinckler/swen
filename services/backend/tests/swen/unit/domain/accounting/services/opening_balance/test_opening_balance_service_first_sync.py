"""Unit tests for OpeningBalanceService.try_create_for_first_sync and has_for_iban.

Domain-only tests: no infrastructure mocks, only AsyncMock for the
AccountRepository and TransactionRepository interfaces.

Covers:
- try_create_for_first_sync happy path: creates and persists an opening balance
- has_for_iban short-circuit: returns OpeningBalanceOutcome(created=False) immediately
- persistence via transaction_repository.save
- edge cases: no transactions, no asset account, no equity account, zero balance
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.services.opening_balance.service import (
    OpeningBalanceOutcome,
    OpeningBalanceService,
)
from swen.domain.accounting.value_objects import Currency
from swen.domain.accounting.well_known_accounts import WellKnownAccounts
from swen.domain.banking.value_objects import BankTransaction

TEST_USER_ID = uuid4()
TEST_IBAN = "DE89370400440532013000"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_asset_account() -> Account:
    return Account(
        name="DKB Girokonto",
        account_type=AccountType.ASSET,
        account_number=TEST_IBAN,
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
        iban=TEST_IBAN,
    )


def _make_equity_account() -> Account:
    return Account(
        name="Anfangssaldo",
        account_type=AccountType.EQUITY,
        account_number=WellKnownAccounts.OPENING_BALANCE_EQUITY,
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
    )


def _make_bank_transaction(
    *,
    booking_date: date = date(2024, 1, 10),
    amount: Decimal = Decimal("100.00"),
) -> BankTransaction:
    return BankTransaction(
        booking_date=booking_date,
        value_date=booking_date,
        amount=amount,
        currency="EUR",
        purpose="Test transaction",
    )


def _make_service(
    *,
    account_repo: AsyncMock | None = None,
    transaction_repo: AsyncMock | None = None,
) -> OpeningBalanceService:
    if account_repo is None:
        account_repo = AsyncMock()
    if transaction_repo is None:
        transaction_repo = AsyncMock()
    return OpeningBalanceService(
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        user_id=TEST_USER_ID,
    )


# ---------------------------------------------------------------------------
# has_for_iban
# ---------------------------------------------------------------------------


class TestHasForIban:
    """has_for_iban delegates to get_date_for_iban."""

    @pytest.mark.asyncio
    async def test_returns_true_when_opening_balance_exists(self):
        transaction_repo = AsyncMock()
        # Simulate a transaction with is_opening_balance metadata for this IBAN
        txn = MagicMock()
        txn.get_metadata_raw.side_effect = lambda key: (
            True if key == "is_opening_balance" else TEST_IBAN
        )
        txn.date = MagicMock()
        txn.date.date.return_value = date(2024, 1, 1)
        transaction_repo.find_by_metadata.return_value = [txn]

        account_repo = AsyncMock()
        service = _make_service(
            account_repo=account_repo, transaction_repo=transaction_repo
        )

        result = await service.has_for_iban(TEST_IBAN)

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_opening_balance(self):
        transaction_repo = AsyncMock()
        transaction_repo.find_by_metadata.return_value = []

        service = _make_service(transaction_repo=transaction_repo)

        result = await service.has_for_iban(TEST_IBAN)

        assert result is False


# ---------------------------------------------------------------------------
# try_create_for_first_sync — short-circuit when OB already exists
# ---------------------------------------------------------------------------


class TestTryCreateForFirstSyncShortCircuit:
    """When has_for_iban returns True, return OpeningBalanceOutcome(created=False)."""

    @pytest.mark.asyncio
    async def test_returns_not_created_when_ob_already_exists(self):
        transaction_repo = AsyncMock()
        # Simulate existing opening balance
        txn = MagicMock()
        txn.get_metadata_raw.side_effect = lambda key: (
            True if key == "is_opening_balance" else TEST_IBAN
        )
        txn.date = MagicMock()
        txn.date.date.return_value = date(2024, 1, 1)
        transaction_repo.find_by_metadata.return_value = [txn]

        account_repo = AsyncMock()
        service = _make_service(
            account_repo=account_repo, transaction_repo=transaction_repo
        )

        outcome = await service.try_create_for_first_sync(
            iban=TEST_IBAN,
            current_balance=Decimal("1000.00"),
            bank_transactions=[_make_bank_transaction()],
        )

        assert outcome == OpeningBalanceOutcome(created=False)

    @pytest.mark.asyncio
    async def test_does_not_persist_when_ob_already_exists(self):
        transaction_repo = AsyncMock()
        txn = MagicMock()
        txn.get_metadata_raw.side_effect = lambda key: (
            True if key == "is_opening_balance" else TEST_IBAN
        )
        txn.date = MagicMock()
        txn.date.date.return_value = date(2024, 1, 1)
        transaction_repo.find_by_metadata.return_value = [txn]

        account_repo = AsyncMock()
        service = _make_service(
            account_repo=account_repo, transaction_repo=transaction_repo
        )

        await service.try_create_for_first_sync(
            iban=TEST_IBAN,
            current_balance=Decimal("1000.00"),
            bank_transactions=[_make_bank_transaction()],
        )

        transaction_repo.save.assert_not_called()


# ---------------------------------------------------------------------------
# try_create_for_first_sync — happy path
# ---------------------------------------------------------------------------


class TestTryCreateForFirstSyncHappyPath:
    """When no OB exists, calculate and persist the opening balance."""

    @pytest.mark.asyncio
    async def test_returns_created_true_on_success(self):
        transaction_repo = AsyncMock()
        # No existing opening balance
        transaction_repo.find_by_metadata.return_value = []

        account_repo = AsyncMock()
        account_repo.find_by_iban.return_value = _make_asset_account()
        account_repo.find_by_account_number.return_value = _make_equity_account()

        service = _make_service(
            account_repo=account_repo, transaction_repo=transaction_repo
        )

        bank_txs = [_make_bank_transaction(amount=Decimal("200.00"))]
        outcome = await service.try_create_for_first_sync(
            iban=TEST_IBAN,
            current_balance=Decimal("1000.00"),
            bank_transactions=bank_txs,
        )

        assert outcome.created is True

    @pytest.mark.asyncio
    async def test_persists_via_transaction_repository_save(self):
        transaction_repo = AsyncMock()
        transaction_repo.find_by_metadata.return_value = []

        account_repo = AsyncMock()
        account_repo.find_by_iban.return_value = _make_asset_account()
        account_repo.find_by_account_number.return_value = _make_equity_account()

        service = _make_service(
            account_repo=account_repo, transaction_repo=transaction_repo
        )

        bank_txs = [_make_bank_transaction(amount=Decimal("200.00"))]
        await service.try_create_for_first_sync(
            iban=TEST_IBAN,
            current_balance=Decimal("1000.00"),
            bank_transactions=bank_txs,
        )

        # Persistence must go through transaction_repository.save
        transaction_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_outcome_amount_matches_calculated_opening_balance(self):
        transaction_repo = AsyncMock()
        transaction_repo.find_by_metadata.return_value = []

        account_repo = AsyncMock()
        account_repo.find_by_iban.return_value = _make_asset_account()
        account_repo.find_by_account_number.return_value = _make_equity_account()

        service = _make_service(
            account_repo=account_repo, transaction_repo=transaction_repo
        )

        # current_balance=1000, net_change=+200 → opening_balance=800
        bank_txs = [_make_bank_transaction(amount=Decimal("200.00"))]
        outcome = await service.try_create_for_first_sync(
            iban=TEST_IBAN,
            current_balance=Decimal("1000.00"),
            bank_transactions=bank_txs,
        )

        assert outcome.amount == Decimal("800.00")


# ---------------------------------------------------------------------------
# try_create_for_first_sync — edge cases
# ---------------------------------------------------------------------------


class TestTryCreateForFirstSyncEdgeCases:
    """Edge cases that result in OpeningBalanceOutcome(created=False)."""

    @pytest.mark.asyncio
    async def test_returns_not_created_when_no_bank_transactions(self):
        transaction_repo = AsyncMock()
        transaction_repo.find_by_metadata.return_value = []

        service = _make_service(transaction_repo=transaction_repo)

        outcome = await service.try_create_for_first_sync(
            iban=TEST_IBAN,
            current_balance=Decimal("1000.00"),
            bank_transactions=[],
        )

        assert outcome == OpeningBalanceOutcome(created=False)

    @pytest.mark.asyncio
    async def test_returns_not_created_when_no_asset_account(self):
        transaction_repo = AsyncMock()
        transaction_repo.find_by_metadata.return_value = []

        account_repo = AsyncMock()
        account_repo.find_by_iban.return_value = None  # no asset account

        service = _make_service(
            account_repo=account_repo, transaction_repo=transaction_repo
        )

        outcome = await service.try_create_for_first_sync(
            iban=TEST_IBAN,
            current_balance=Decimal("1000.00"),
            bank_transactions=[_make_bank_transaction()],
        )

        assert outcome == OpeningBalanceOutcome(created=False)

    @pytest.mark.asyncio
    async def test_returns_not_created_when_no_equity_account(self):
        transaction_repo = AsyncMock()
        transaction_repo.find_by_metadata.return_value = []

        account_repo = AsyncMock()
        account_repo.find_by_iban.return_value = _make_asset_account()
        account_repo.find_by_account_number.return_value = None  # no equity account

        service = _make_service(
            account_repo=account_repo, transaction_repo=transaction_repo
        )

        outcome = await service.try_create_for_first_sync(
            iban=TEST_IBAN,
            current_balance=Decimal("1000.00"),
            bank_transactions=[_make_bank_transaction()],
        )

        assert outcome == OpeningBalanceOutcome(created=False)

    @pytest.mark.asyncio
    async def test_returns_not_created_when_opening_balance_is_zero(self):
        """Zero opening balance means no transaction is created."""
        transaction_repo = AsyncMock()
        transaction_repo.find_by_metadata.return_value = []

        account_repo = AsyncMock()
        account_repo.find_by_iban.return_value = _make_asset_account()
        account_repo.find_by_account_number.return_value = _make_equity_account()

        service = _make_service(
            account_repo=account_repo, transaction_repo=transaction_repo
        )

        # current_balance == net_change → opening balance = 0
        bank_txs = [_make_bank_transaction(amount=Decimal("1000.00"))]
        outcome = await service.try_create_for_first_sync(
            iban=TEST_IBAN,
            current_balance=Decimal("1000.00"),
            bank_transactions=bank_txs,
        )

        assert outcome == OpeningBalanceOutcome(created=False)
        transaction_repo.save.assert_not_called()
