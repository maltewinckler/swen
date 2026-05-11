"""Unit tests for BankBalanceService.get_for_iban.

Covers:
1. DB hit: when bank_account_repo.find_balance returns a value, return it.
2. None: when DB returns None, return None (no bank fetch fallback).
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from swen.domain.banking.services.bank_balance_service import (
    BankBalanceService,
)

TEST_IBAN = "DE89370400440532013000"


def _make_service(
    *, db_balance: Decimal | None = None
) -> tuple[BankBalanceService, AsyncMock]:
    bank_account_repo = AsyncMock()
    bank_account_repo.find_balance.return_value = db_balance

    service = BankBalanceService(
        bank_fetch_service=AsyncMock(),
        bank_account_repo=bank_account_repo,
        credential_repo=AsyncMock(),
    )
    return service, bank_account_repo


# ---------------------------------------------------------------------------
# DB hit
# ---------------------------------------------------------------------------


class TestDbHit:
    """When find_balance returns a value, return it."""

    @pytest.mark.asyncio
    async def test_returns_db_balance_when_found(self):
        service, _ = _make_service(db_balance=Decimal("1234.56"))

        result = await service.get_for_iban(TEST_IBAN)

        assert result == Decimal("1234.56")

    @pytest.mark.asyncio
    async def test_calls_find_balance_with_correct_iban(self):
        service, bank_account_repo = _make_service(db_balance=Decimal("100.00"))

        await service.get_for_iban(TEST_IBAN)

        bank_account_repo.find_balance.assert_awaited_once_with(TEST_IBAN)


# ---------------------------------------------------------------------------
# None when no stored balance
# ---------------------------------------------------------------------------


class TestNoneWhenNoBalance:
    """Returns None when the DB has no stored balance for the IBAN."""

    @pytest.mark.asyncio
    async def test_returns_none_when_db_miss(self):
        service, _ = _make_service(db_balance=None)

        result = await service.get_for_iban(TEST_IBAN)

        assert result is None
