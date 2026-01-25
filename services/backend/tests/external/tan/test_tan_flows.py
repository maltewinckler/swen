"""Tests that require TAN approval via app (manual intervention).

These tests connect to real banks and require TAN approval.
Run with: pytest tests/external/tan/ --run-external

WARNING: These tests require manual intervention - you must approve
TAN requests in your banking app when prompted.
"""

import os
from datetime import timedelta
from pathlib import Path

import pytest
from dotenv import load_dotenv

from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.domain.shared.time import today_utc
from swen.infrastructure.banking.geldstrom_adapter import GeldstromAdapter

# Load environment variables from repository root
root_dir = Path(__file__).parent.parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)


def _env_flag(name: str) -> bool:
    """Return True if the given environment flag is truthy."""
    return os.getenv(name, "").lower() in ("1", "true", "yes")


RUN_MANUAL_TAN = _env_flag("RUN_MANUAL_TAN")


@pytest.fixture(scope="module")
def credentials():
    """Load real bank credentials from environment variables."""
    blz = os.getenv("FINTS_BLZ")
    username = os.getenv("FINTS_USERNAME")
    pin = os.getenv("FINTS_PIN")
    endpoint = os.getenv("FINTS_ENDPOINT")

    missing = []
    if not blz:
        missing.append("FINTS_BLZ")
    if not username:
        missing.append("FINTS_USERNAME")
    if not pin:
        missing.append("FINTS_PIN")
    if not endpoint:
        missing.append("FINTS_ENDPOINT")

    if missing:
        pytest.skip(f"Missing credentials in .env: {', '.join(missing)}")

    assert blz is not None
    assert username is not None
    assert pin is not None
    assert endpoint is not None

    if not blz.isdigit() or len(blz) != 8:
        pytest.skip(f"Invalid FINTS_BLZ format: {blz}. Must be 8 digits.")

    return BankCredentials.from_plain(
        blz=blz,
        username=username,
        pin=pin,
        endpoint=endpoint,
    )


@pytest.fixture(scope="module")
def tan_settings():
    """Load TAN settings from environment variables."""
    tan_method = os.getenv("FINTS_TAN_METHOD")
    tan_medium = os.getenv("FINTS_TAN_MEDIUM")

    if not tan_method or not tan_medium:
        pytest.skip(
            "Missing TAN settings in .env: FINTS_TAN_METHOD, FINTS_TAN_MEDIUM.",
        )

    return {"tan_method": tan_method, "tan_medium": tan_medium}


@pytest.mark.tan
@pytest.mark.manual
class TestTANFlow:
    """Tests that require TAN approval via app (decoupled TAN).

    Geldstrom handles decoupled TAN (SecureGo, pushTAN) internally via polling.
    These tests verify that long transaction history fetches work when TAN
    is required - you need to approve in your banking app when prompted.
    """

    @pytest.mark.asyncio
    async def test_long_history_with_tan_polling(self, credentials, tan_settings):
        """Fetch 200+ days of transactions - approve TAN in banking app when prompted.

        Geldstrom automatically detects when TAN is required and polls for
        approval. You'll see logs like:
            "Decoupled TAN required for operation - waiting for app approval..."
            "Polling for decoupled TAN approval..."

        Approve the request in your banking app (e.g., SecureGo) to continue.
        """
        if not RUN_MANUAL_TAN:
            pytest.skip(
                "Manual TAN tests disabled. Set RUN_MANUAL_TAN=1 "
                "to enable TAN flow (approve in banking app).",
            )

        adapter = GeldstromAdapter()
        adapter.set_tan_method(tan_settings["tan_method"])
        adapter.set_tan_medium(tan_settings["tan_medium"])

        try:
            await adapter.connect(credentials)

            accounts = await adapter.fetch_accounts()
            if not accounts:
                pytest.skip("No accounts available")

            iban = accounts[0].iban
            start_date = today_utc() - timedelta(days=200)

            print(f"\n📱 Fetching {200} days of history for {iban}...")
            print("   If TAN is required, approve it in your banking app!")

            transactions = await adapter.fetch_transactions(iban, start_date=start_date)

            print(f"Successfully fetched {len(transactions)} transactions")

            # Long history should return substantial transactions
            assert len(transactions) > 0, "Expected transactions for 200-day history"

        finally:
            if adapter.is_connected():
                await adapter.disconnect()
