"""Integration tests for the Geldstrom API adapter (gateway HTTP path).

These tests connect to the real Geldstrom Gateway API and verify that the
GeldstromApiAdapter ACL works end-to-end.

Requirements:
- GATEWAY_API_KEY set in root .env
- FINTS_BLZ, FINTS_USERNAME, FINTS_PIN, FINTS_ENDPOINT set in root .env
- Network access to the gateway

Run with: pytest tests/external/gateway/ --run-external
TAN tests: pytest tests/external/gateway/ --run-external -m tan
"""

import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from dotenv import load_dotenv

from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.domain.shared.time import today_utc
from swen.infrastructure.banking.geldstrom_api.adapter import (
    GeldstromApiAdapter,
)
from swen.infrastructure.banking.geldstrom_api.config import GeldstromApiConfig

# Load environment variables from repository root
_root_dir = Path(__file__).parent.parent.parent.parent.parent.parent
_env_path = _root_dir / ".env"
load_dotenv(dotenv_path=_env_path)


# ═══════════════════════════════════════════════════════════════
#                        Helpers
# ═══════════════════════════════════════════════════════════════


class _StaticConfigRepo:
    """In-memory config repo that returns values read from .env."""

    def __init__(self, api_key: str, endpoint_url: str) -> None:
        self._config = GeldstromApiConfig(
            api_key=api_key,
            endpoint_url=endpoint_url,
            is_active=True,
        )

    async def get_configuration(self) -> GeldstromApiConfig:
        return self._config

    async def is_active(self) -> bool:
        return True


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").lower() in ("1", "true", "yes")


# ═══════════════════════════════════════════════════════════════
#                        Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def credentials():
    """Load bank credentials from .env."""
    blz = os.getenv("FINTS_BLZ")
    username = os.getenv("FINTS_USERNAME")
    pin = os.getenv("FINTS_PIN")
    endpoint = os.getenv("FINTS_ENDPOINT")

    missing = [
        k
        for k, v in [
            ("FINTS_BLZ", blz),
            ("FINTS_USERNAME", username),
            ("FINTS_PIN", pin),
            ("FINTS_ENDPOINT", endpoint),
        ]
        if not v
    ]
    if missing:
        pytest.skip(f"Missing .env vars: {', '.join(missing)}")

    assert blz
    assert username
    assert pin
    assert endpoint
    return BankCredentials.from_plain(
        blz=blz,
        username=username,
        pin=pin,
    )


@pytest.fixture(scope="module")
def config_repo():
    """Build a static config repo from .env."""
    api_key = os.getenv("GATEWAY_API_KEY")
    if not api_key:
        pytest.skip("GATEWAY_API_KEY not set in .env")

    return _StaticConfigRepo(
        api_key=api_key,
        endpoint_url="https://geldstrom-api.de",
    )


@pytest.fixture
def adapter(config_repo):
    """Create an adapter wired to the real gateway."""
    a = GeldstromApiAdapter(config_repository=config_repo)
    a.set_tan_method("946")
    return a


# ═══════════════════════════════════════════════════════════════
#                 Non-TAN tests (immediate 200)
# ═══════════════════════════════════════════════════════════════


class TestGeldstromApiTanMethods:
    """Querying TAN methods never requires TAN."""

    @pytest.mark.asyncio
    async def test_get_tan_methods(self, adapter, credentials):
        methods = await adapter.get_tan_methods(credentials)

        assert len(methods) >= 1
        assert methods[0].code
        assert methods[0].name


class TestGeldstromApiConnect:
    """Connecting (listing accounts) should return instantly for <90d."""

    @pytest.mark.asyncio
    async def test_connect_and_list_accounts(self, adapter, credentials):
        ok = await adapter.connect(credentials)

        assert ok is True
        assert adapter.is_connected()

        accounts = await adapter.fetch_accounts()
        assert len(accounts) >= 1
        assert accounts[0].iban
        assert accounts[0].currency == "EUR"

        await adapter.disconnect()
        assert not adapter.is_connected()

    @pytest.mark.asyncio
    async def test_disconnect_is_idempotent(self, adapter, credentials):
        await adapter.connect(credentials)
        await adapter.disconnect()
        await adapter.disconnect()  # should not raise
        assert not adapter.is_connected()


class TestGeldstromApiTransactionsShort:
    """Short-range transaction fetches (≤90 days, no TAN)."""

    @pytest.mark.asyncio
    async def test_fetch_recent_transactions(self, adapter, credentials):
        await adapter.connect(credentials)
        accounts = await adapter.fetch_accounts()
        iban = accounts[0].iban

        start = today_utc() - timedelta(days=30)
        txns = await adapter.fetch_transactions(iban, start_date=start)

        assert isinstance(txns, list)
        assert len(txns) > 0, "Expected at least 1 transaction in the last 30 days"

        txn = txns[0]
        assert txn.booking_date is not None
        assert isinstance(txn.amount, Decimal)
        assert txn.currency

        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_fetch_transactions_with_date_range(
        self,
        adapter,
        credentials,
    ):
        await adapter.connect(credentials)
        accounts = await adapter.fetch_accounts()
        iban = accounts[0].iban

        end = today_utc()
        start = end - timedelta(days=14)
        txns = await adapter.fetch_transactions(
            iban,
            start_date=start,
            end_date=end,
        )

        assert isinstance(txns, list)
        for txn in txns:
            assert start <= txn.booking_date <= end

        await adapter.disconnect()


# ═══════════════════════════════════════════════════════════════
#        TAN tests (202 → poll → 200, requires app approval)
# ═══════════════════════════════════════════════════════════════


RUN_MANUAL_TAN = _env_flag("RUN_MANUAL_TAN")


@pytest.mark.tan
@pytest.mark.manual
class TestGeldstromApiTransactionsWithTAN:
    """Long-range fetches that require decoupled TAN approval.

    These tests trigger a 202 (pending_confirmation) response and poll
    via POST /v1/banking/operations/{id}/poll until approval.

    Run with: RUN_MANUAL_TAN=1 pytest tests/external/gateway/ --run-external -m tan
    """

    @pytest.mark.asyncio
    async def test_long_history_triggers_polling(self, adapter, credentials):
        """Fetch 365 days of transactions — approve TAN in SecureGo+."""
        if not RUN_MANUAL_TAN:
            pytest.skip(
                "Manual TAN tests disabled. Set RUN_MANUAL_TAN=1 to enable.",
            )

        await adapter.connect(credentials)
        accounts = await adapter.fetch_accounts()
        iban = accounts[0].iban

        start = today_utc() - timedelta(days=365)
        txns = await adapter.fetch_transactions(iban, start_date=start)

        assert len(txns) > 0, "Expected transactions for 365-day history"
        # 365-day range should return substantially more than 30-day
        assert len(txns) > 30, (
            f"Expected >30 txns for a year of history, got {len(txns)}"
        )

        await adapter.disconnect()
