"""Unit tests for SyncPeriodResolver.

Covers:
- resolve_fixed: window math (today - days .. today, non-adaptive)
- resolve_adaptive_for: next-day-after-last-success from import history
- resolve_adaptive_for: today-90-days fallback when no successful import exists
- resolve_adaptive_for: today-90-days fallback when import list is empty
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from swen.application.services.integration.sync_period_resolver import (
    _ADAPTIVE_FALLBACK_DAYS,
    SyncPeriodResolver,
)
from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.value_objects import ImportStatus

TEST_USER_ID = uuid4()
TEST_IBAN = "DE89370400440532013000"

# Fixed "today" for deterministic tests
_TODAY = date(2024, 6, 15)


def _make_import_repo(imports: list) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_iban.return_value = imports
    return repo


def _make_successful_import(
    *,
    booking_date: date,
    iban: str = TEST_IBAN,
) -> TransactionImport:
    """Create a successful TransactionImport with a booking date encoded in the identity hash."""
    bank_tx_id = uuid4()
    record = TransactionImport(
        user_id=TEST_USER_ID,
        bank_transaction_id=bank_tx_id,
        status=ImportStatus.PENDING,
    )
    # Manually set to SUCCESS with an accounting transaction ID
    accounting_tx_id = uuid4()
    record.mark_as_imported(accounting_tx_id)

    # Patch the bank_transaction_identity attribute to encode the booking date
    # Format: "<hash>|<YYYY-MM-DD>|..."
    object.__setattr__(
        record,
        "_bank_transaction_identity",
        f"somehash|{booking_date.isoformat()}|extra",
    )
    return record


def _make_failed_import(*, booking_date: date) -> TransactionImport:
    """Create a failed TransactionImport."""
    bank_tx_id = uuid4()
    record = TransactionImport(
        user_id=TEST_USER_ID,
        bank_transaction_id=bank_tx_id,
        status=ImportStatus.PENDING,
    )
    record.mark_as_failed("some error")
    object.__setattr__(
        record,
        "_bank_transaction_identity",
        f"somehash|{booking_date.isoformat()}|extra",
    )
    return record


# ---------------------------------------------------------------------------
# resolve_fixed
# ---------------------------------------------------------------------------


class TestResolveFixed:
    """resolve_fixed returns a non-adaptive window of today - days .. today."""

    def test_start_date_is_today_minus_days(self):
        repo = _make_import_repo([])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=30)

        assert period.start_date == _TODAY - timedelta(days=30)

    def test_end_date_is_today(self):
        repo = _make_import_repo([])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=30)

        assert period.end_date == _TODAY

    def test_period_is_not_adaptive(self):
        repo = _make_import_repo([])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=7)

        assert period.adaptive is False

    def test_window_width_matches_days_parameter(self):
        repo = _make_import_repo([])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=90)

        assert (period.end_date - period.start_date).days == 90

    def test_zero_days_gives_same_start_and_end(self):
        repo = _make_import_repo([])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = resolver.resolve_fixed(days=0)

        assert period.start_date == period.end_date == _TODAY


# ---------------------------------------------------------------------------
# resolve_adaptive_for — fallback (no successful imports)
# ---------------------------------------------------------------------------


class TestResolveAdaptiveForFallback:
    """Falls back to today - 90 days when no successful import exists."""

    @pytest.mark.asyncio
    async def test_fallback_when_no_imports(self):
        repo = _make_import_repo([])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.start_date == _TODAY - timedelta(days=_ADAPTIVE_FALLBACK_DAYS)
        assert period.end_date == _TODAY

    @pytest.mark.asyncio
    async def test_fallback_when_only_failed_imports(self):
        failed = _make_failed_import(booking_date=date(2024, 5, 1))
        repo = _make_import_repo([failed])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.start_date == _TODAY - timedelta(days=_ADAPTIVE_FALLBACK_DAYS)

    @pytest.mark.asyncio
    async def test_fallback_period_is_adaptive(self):
        repo = _make_import_repo([])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.adaptive is True

    @pytest.mark.asyncio
    async def test_calls_find_by_iban_with_correct_iban(self):
        repo = _make_import_repo([])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            await resolver.resolve_adaptive_for(TEST_IBAN)

        repo.find_by_iban.assert_awaited_once_with(TEST_IBAN)


# ---------------------------------------------------------------------------
# resolve_adaptive_for — next-day-after-last-success
# ---------------------------------------------------------------------------


class TestResolveAdaptiveForNextDay:
    """Returns next-day-after-last-success when successful imports exist."""

    @pytest.mark.asyncio
    async def test_start_is_day_after_latest_booking_date(self):
        last_booking = date(2024, 5, 20)
        successful = _make_successful_import_with_identity(
            booking_date=last_booking,
        )
        repo = _make_import_repo([successful])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.start_date == last_booking + timedelta(days=1)

    @pytest.mark.asyncio
    async def test_uses_latest_booking_date_among_multiple_successes(self):
        imports = [
            _make_successful_import_with_identity(booking_date=date(2024, 4, 10)),
            _make_successful_import_with_identity(booking_date=date(2024, 5, 20)),
            _make_successful_import_with_identity(booking_date=date(2024, 3, 5)),
        ]
        repo = _make_import_repo(imports)
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        # Latest is 2024-05-20, so start = 2024-05-21
        assert period.start_date == date(2024, 5, 21)

    @pytest.mark.asyncio
    async def test_start_capped_at_today_when_next_day_is_in_future(self):
        """If last booking was yesterday, start = today (not tomorrow)."""
        yesterday = _TODAY - timedelta(days=1)
        successful = _make_successful_import_with_identity(booking_date=yesterday)
        repo = _make_import_repo([successful])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        # next_sync_start = yesterday + 1 = today → capped at today
        assert period.start_date == _TODAY

    @pytest.mark.asyncio
    async def test_end_date_is_always_today(self):
        successful = _make_successful_import_with_identity(
            booking_date=date(2024, 5, 1)
        )
        repo = _make_import_repo([successful])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.end_date == _TODAY

    @pytest.mark.asyncio
    async def test_period_is_adaptive(self):
        successful = _make_successful_import_with_identity(
            booking_date=date(2024, 5, 1)
        )
        repo = _make_import_repo([successful])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        assert period.adaptive is True

    @pytest.mark.asyncio
    async def test_failed_imports_ignored_when_successful_exist(self):
        """Failed imports should not affect the start date calculation."""
        successful = _make_successful_import_with_identity(
            booking_date=date(2024, 5, 10)
        )
        failed = _make_failed_import(booking_date=date(2024, 6, 1))
        repo = _make_import_repo([successful, failed])
        resolver = SyncPeriodResolver(import_repo=repo)

        with patch(
            "swen.application.services.integration.sync_period_resolver.today_utc",
            return_value=_TODAY,
        ):
            period = await resolver.resolve_adaptive_for(TEST_IBAN)

        # Only the successful import's date matters
        assert period.start_date == date(2024, 5, 11)


# ---------------------------------------------------------------------------
# Helper that creates a successful import with identity hash
# ---------------------------------------------------------------------------


def _make_successful_import_with_identity(*, booking_date: date) -> TransactionImport:
    """Create a successful TransactionImport with booking date in identity hash."""
    bank_tx_id = uuid4()
    record = TransactionImport(
        user_id=TEST_USER_ID,
        bank_transaction_id=bank_tx_id,
        status=ImportStatus.PENDING,
    )
    accounting_tx_id = uuid4()
    record.mark_as_imported(accounting_tx_id)

    # The resolver reads bank_transaction_identity via getattr
    # We need to set it as an attribute on the instance
    object.__setattr__(
        record,
        "bank_transaction_identity",
        f"somehash|{booking_date.isoformat()}|extra",
    )
    return record
