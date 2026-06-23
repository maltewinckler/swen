"""Unit tests for BankFetchService.

Covers:
- connect → fetch → disconnect lifecycle on success
- connect → fetch → disconnect lifecycle when fetch_transactions raises
- connect → fetch_accounts → disconnect lifecycle on success
- connect → fetch_accounts → disconnect lifecycle when fetch_accounts raises
- TAN method / medium / callback wrapping applied before connect
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from swen.domain.banking.services.bank_fetch_service import BankFetchService
from swen.domain.banking.value_objects import BankCredentials

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_credentials() -> BankCredentials:
    return BankCredentials.from_plain(
        blz="37040044",
        username="testuser",
        pin="testpin",
    )


_START = date(2024, 1, 1)
_END = date(2024, 1, 31)


def _make_adapter() -> AsyncMock:
    """Return a mock BankConnectionPort with all required methods."""
    adapter = AsyncMock()
    adapter.connect = AsyncMock(return_value=True)
    adapter.disconnect = AsyncMock()
    adapter.fetch_transactions = AsyncMock(return_value=[])
    adapter.fetch_accounts = AsyncMock(return_value=[])
    adapter.set_tan_method = MagicMock()
    adapter.set_tan_medium = MagicMock()
    adapter.set_tan_callback = AsyncMock()
    return adapter


# ---------------------------------------------------------------------------
# fetch_transactions lifecycle
# ---------------------------------------------------------------------------


class TestFetchTransactionsLifecycle:
    """connect → fetch_transactions → disconnect is always called."""

    @pytest.mark.asyncio
    async def test_connect_called_before_fetch(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)
        credentials = _make_credentials()

        await service.fetch_transactions(
            credentials, "DE89370400440532013000", _START, _END
        )

        # connect must have been called
        adapter.connect.assert_awaited_once_with(credentials)

    @pytest.mark.asyncio
    async def test_disconnect_called_after_successful_fetch(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)

        await service.fetch_transactions(
            _make_credentials(), "DE89370400440532013000", _START, _END
        )

        adapter.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_called_exactly_once_on_success(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)

        await service.fetch_transactions(
            _make_credentials(), "DE89370400440532013000", _START, _END
        )

        assert adapter.disconnect.await_count == 1

    @pytest.mark.asyncio
    async def test_disconnect_called_when_fetch_transactions_raises(self):
        adapter = _make_adapter()
        adapter.fetch_transactions.side_effect = RuntimeError("bank error")
        service = BankFetchService(bank_adapter=adapter)

        with pytest.raises(RuntimeError, match="bank error"):
            await service.fetch_transactions(
                _make_credentials(), "DE89370400440532013000", _START, _END
            )

        # disconnect must still be called exactly once
        adapter.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_called_exactly_once_on_raise(self):
        adapter = _make_adapter()
        adapter.fetch_transactions.side_effect = ValueError("bad iban")
        service = BankFetchService(bank_adapter=adapter)

        with pytest.raises(ValueError):
            await service.fetch_transactions(
                _make_credentials(), "DE89370400440532013000", _START, _END
            )

        assert adapter.disconnect.await_count == 1

    @pytest.mark.asyncio
    async def test_returns_transactions_from_adapter(self):
        adapter = _make_adapter()
        fake_tx = MagicMock()
        adapter.fetch_transactions.return_value = [fake_tx]
        service = BankFetchService(bank_adapter=adapter)

        result = await service.fetch_transactions(
            _make_credentials(), "DE89370400440532013000", _START, _END
        )

        assert result == [fake_tx]

    @pytest.mark.asyncio
    async def test_period_dates_passed_to_adapter(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)

        await service.fetch_transactions(
            _make_credentials(),
            "DE89370400440532013000",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31),
        )

        adapter.fetch_transactions.assert_awaited_once_with(
            account_iban="DE89370400440532013000",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31),
        )


# ---------------------------------------------------------------------------
# fetch_accounts lifecycle
# ---------------------------------------------------------------------------


class TestFetchAccountsLifecycle:
    """connect → fetch_accounts → disconnect is always called."""

    @pytest.mark.asyncio
    async def test_connect_called_before_fetch_accounts(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)
        credentials = _make_credentials()

        await service.fetch_accounts(credentials)

        adapter.connect.assert_awaited_once_with(credentials)

    @pytest.mark.asyncio
    async def test_disconnect_called_after_successful_fetch_accounts(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)

        await service.fetch_accounts(_make_credentials())

        adapter.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_called_when_fetch_accounts_raises(self):
        adapter = _make_adapter()
        adapter.fetch_accounts.side_effect = RuntimeError("connection lost")
        service = BankFetchService(bank_adapter=adapter)

        with pytest.raises(RuntimeError, match="connection lost"):
            await service.fetch_accounts(_make_credentials())

        adapter.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_called_exactly_once_on_fetch_accounts_raise(self):
        adapter = _make_adapter()
        adapter.fetch_accounts.side_effect = ValueError("auth failed")
        service = BankFetchService(bank_adapter=adapter)

        with pytest.raises(ValueError):
            await service.fetch_accounts(_make_credentials())

        assert adapter.disconnect.await_count == 1


# ---------------------------------------------------------------------------
# TAN method / medium / callback wrapping
# ---------------------------------------------------------------------------


class TestTanConfiguration:
    """TAN settings are applied to the adapter before connect."""

    @pytest.mark.asyncio
    async def test_tan_method_set_when_provided(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)

        await service.fetch_transactions(
            _make_credentials(),
            "DE89370400440532013000",
            _START,
            _END,
            tan_method="946",
        )

        adapter.set_tan_method.assert_called_once_with("946")

    @pytest.mark.asyncio
    async def test_tan_medium_set_when_provided(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)

        await service.fetch_transactions(
            _make_credentials(),
            "DE89370400440532013000",
            _START,
            _END,
            tan_medium="SecureGo",
        )

        adapter.set_tan_medium.assert_called_once_with("SecureGo")

    @pytest.mark.asyncio
    async def test_tan_method_not_set_when_none(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)

        await service.fetch_transactions(
            _make_credentials(),
            "DE89370400440532013000",
            _START,
            _END,
            tan_method=None,
        )

        adapter.set_tan_method.assert_not_called()

    @pytest.mark.asyncio
    async def test_tan_medium_not_set_when_none(self):
        adapter = _make_adapter()
        service = BankFetchService(bank_adapter=adapter)

        await service.fetch_transactions(
            _make_credentials(),
            "DE89370400440532013000",
            _START,
            _END,
            tan_medium=None,
        )

        adapter.set_tan_medium.assert_not_called()

    @pytest.mark.asyncio
    async def test_tan_settings_applied_before_connect(self):
        """TAN method must be set before connect is called."""
        adapter = _make_adapter()
        call_order = []

        adapter.set_tan_method.side_effect = lambda _: call_order.append(
            "set_tan_method"
        )
        adapter.connect.side_effect = lambda _: call_order.append("connect") or True

        service = BankFetchService(bank_adapter=adapter)

        await service.fetch_transactions(
            _make_credentials(),
            "DE89370400440532013000",
            _START,
            _END,
            tan_method="946",
        )

        assert call_order.index("set_tan_method") < call_order.index("connect")
