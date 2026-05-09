"""Unit tests for BankBalanceService.get_for_iban.

Covers three acceptance criteria:
1. DB-first hit: when bank_account_repo.find_balance returns a value, return it
   without touching the bank.
2. Fallback: when DB returns None, fetch accounts from bank, persist via
   BankAccountRepository.save_accounts, then return the matching balance.
3. None: when neither DB nor bank fetch returns a balance for the IBAN,
   return None.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from swen.domain.banking.services.bank_balance_service import (
    BankBalanceService,
)
from swen.domain.banking.value_objects import BankAccount, BankCredentials

TEST_IBAN = "DE89370400440532013000"
OTHER_IBAN = "DE12500000001234567890"


def _make_credentials() -> BankCredentials:
    return BankCredentials.from_plain(
        blz="37040044",
        username="testuser",
        pin="testpin",
    )


def _make_bank_account(iban: str, balance: Decimal | None) -> BankAccount:
    return BankAccount(
        iban=iban,
        account_number="532013000",
        blz="37040044",
        account_holder="Test User",
        account_type="Girokonto",
        currency="EUR",
        balance=balance,
    )


def _make_service(
    *,
    db_balance: Decimal | None = None,
    fetched_accounts: list | None = None,
) -> tuple[BankBalanceService, AsyncMock, AsyncMock]:
    """Build a BankBalanceService with mocked dependencies.

    Returns (service, bank_account_repo, bank_fetch_service).
    """
    bank_account_repo = AsyncMock()
    bank_account_repo.find_balance.return_value = db_balance
    bank_account_repo.save_accounts = AsyncMock()

    bank_fetch_service = AsyncMock()
    if fetched_accounts is not None:
        bank_fetch_service.fetch_accounts.return_value = fetched_accounts
    else:
        bank_fetch_service.fetch_accounts.return_value = []

    service = BankBalanceService(
        bank_fetch_service=bank_fetch_service,
        bank_account_repo=bank_account_repo,
        credential_repo=AsyncMock(),
    )
    return service, bank_account_repo, bank_fetch_service


# ---------------------------------------------------------------------------
# AC 1: DB-first hit
# ---------------------------------------------------------------------------


class TestDbFirstHit:
    """When find_balance returns a value, return it without touching the bank."""

    @pytest.mark.asyncio
    async def test_returns_db_balance_when_found(self):
        service, _, _ = _make_service(db_balance=Decimal("1234.56"))

        result = await service.get_for_iban(TEST_IBAN, _make_credentials())

        assert result == Decimal("1234.56")

    @pytest.mark.asyncio
    async def test_does_not_call_fetch_accounts_when_db_hit(self):
        service, _, bank_fetch = _make_service(db_balance=Decimal("500.00"))

        await service.get_for_iban(TEST_IBAN, _make_credentials())

        bank_fetch.fetch_accounts.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_call_save_accounts_when_db_hit(self):
        service, bank_account_repo, _ = _make_service(db_balance=Decimal("500.00"))

        await service.get_for_iban(TEST_IBAN, _make_credentials())

        bank_account_repo.save_accounts.assert_not_called()

    @pytest.mark.asyncio
    async def test_calls_find_balance_with_correct_iban(self):
        service, bank_account_repo, _ = _make_service(db_balance=Decimal("100.00"))

        await service.get_for_iban(TEST_IBAN, _make_credentials())

        bank_account_repo.find_balance.assert_awaited_once_with(TEST_IBAN)


# ---------------------------------------------------------------------------
# AC 2: Fallback — fetch accounts and persist
# ---------------------------------------------------------------------------


class TestFallbackFetchAndPersist:
    """When DB returns None, fetch accounts, persist, return matching balance."""

    @pytest.mark.asyncio
    async def test_returns_balance_from_fetched_accounts(self):
        fetched = [_make_bank_account(TEST_IBAN, Decimal("999.00"))]
        service, _, _ = _make_service(db_balance=None, fetched_accounts=fetched)

        result = await service.get_for_iban(TEST_IBAN, _make_credentials())

        assert result == Decimal("999.00")

    @pytest.mark.asyncio
    async def test_calls_fetch_accounts_when_db_miss(self):
        fetched = [_make_bank_account(TEST_IBAN, Decimal("100.00"))]
        service, _, bank_fetch = _make_service(
            db_balance=None, fetched_accounts=fetched
        )

        await service.get_for_iban(TEST_IBAN, _make_credentials())

        bank_fetch.fetch_accounts.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persists_fetched_accounts_via_save_accounts(self):
        fetched = [_make_bank_account(TEST_IBAN, Decimal("100.00"))]
        service, bank_account_repo, _ = _make_service(
            db_balance=None, fetched_accounts=fetched
        )

        await service.get_for_iban(TEST_IBAN, _make_credentials())

        bank_account_repo.save_accounts.assert_awaited_once_with(fetched)

    @pytest.mark.asyncio
    async def test_returns_correct_iban_balance_when_multiple_accounts_fetched(self):
        fetched = [
            _make_bank_account(OTHER_IBAN, Decimal("500.00")),
            _make_bank_account(TEST_IBAN, Decimal("750.00")),
        ]
        service, _, _ = _make_service(db_balance=None, fetched_accounts=fetched)

        result = await service.get_for_iban(TEST_IBAN, _make_credentials())

        assert result == Decimal("750.00")

    @pytest.mark.asyncio
    async def test_passes_credentials_to_fetch_accounts(self):
        fetched = [_make_bank_account(TEST_IBAN, Decimal("100.00"))]
        service, _, bank_fetch = _make_service(
            db_balance=None, fetched_accounts=fetched
        )
        credentials = _make_credentials()

        await service.get_for_iban(TEST_IBAN, credentials)

        bank_fetch.fetch_accounts.assert_awaited_once_with(credentials)


# ---------------------------------------------------------------------------
# AC 3: None when neither source returns a balance
# ---------------------------------------------------------------------------


class TestNoneWhenNoBalance:
    """Returns None when neither DB nor bank fetch provides a balance."""

    @pytest.mark.asyncio
    async def test_returns_none_when_db_miss_and_no_fetched_accounts(self):
        service, _, _ = _make_service(db_balance=None, fetched_accounts=[])

        result = await service.get_for_iban(TEST_IBAN, _make_credentials())

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_fetched_accounts_have_no_matching_iban(self):
        fetched = [_make_bank_account(OTHER_IBAN, Decimal("100.00"))]
        service, _, _ = _make_service(db_balance=None, fetched_accounts=fetched)

        result = await service.get_for_iban(TEST_IBAN, _make_credentials())

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_matching_account_has_no_balance(self):
        fetched = [_make_bank_account(TEST_IBAN, None)]
        service, _, _ = _make_service(db_balance=None, fetched_accounts=fetched)

        result = await service.get_for_iban(TEST_IBAN, _make_credentials())

        assert result is None

    @pytest.mark.asyncio
    async def test_still_persists_accounts_even_when_no_matching_balance(self):
        """save_accounts is called even if the target IBAN has no balance."""
        fetched = [_make_bank_account(OTHER_IBAN, Decimal("100.00"))]
        service, bank_account_repo, _ = _make_service(
            db_balance=None, fetched_accounts=fetched
        )

        await service.get_for_iban(TEST_IBAN, _make_credentials())

        bank_account_repo.save_accounts.assert_awaited_once_with(fetched)
