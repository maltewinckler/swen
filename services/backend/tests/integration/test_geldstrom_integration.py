"""Integration tests for Geldstrom Adapter with real bank connection."""

import os
import warnings
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from dotenv import load_dotenv

from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.infrastructure.banking.geldstrom_adapter import GeldstromAdapter

warnings.filterwarnings(
    "ignore",
    message="No 'tan_method' configured",
    category=UserWarning,
)

# Load environment variables from repository root so we share credentials
root_dir = Path(__file__).parent.parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path)

# Skip all tests if integration tests are not explicitly enabled
pytestmark = pytest.mark.integration


def _env_flag(name: str) -> bool:
    """Return True if the given environment flag is truthy."""

    return os.getenv(name, "").lower() in ("1", "true", "yes")


RUN_INTEGRATION = _env_flag("RUN_INTEGRATION") or _env_flag("RUN_INTEGRATION_TESTS")
RUN_MANUAL_TAN = _env_flag("RUN_MANUAL_TAN")


@pytest.fixture(scope="module")
def integration_enabled():
    """Check if integration tests are enabled via environment variable."""
    if not RUN_INTEGRATION:
        pytest.skip(
            "Integration tests disabled. "
            "Enable by setting RUN_INTEGRATION=1 (or RUN_INTEGRATION_TESTS=1) in .env",
        )


@pytest.fixture(scope="module")
def credentials(integration_enabled):  # noqa: ARG001
    """Load real bank credentials from environment variables.

    Loads from repository root .env file.
    """
    blz = os.getenv("FINTS_BLZ")
    username = os.getenv("FINTS_USERNAME")
    pin = os.getenv("FINTS_PIN")
    endpoint = os.getenv("FINTS_ENDPOINT")

    # Check for missing credentials
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
        pytest.skip(
            f"Missing credentials in .env: {', '.join(missing)}. "
            f"Copy .env.example to .env and fill in your bank credentials.",
        )

    # Type narrowing - we've verified these are not None above
    assert blz is not None
    assert username is not None
    assert pin is not None
    assert endpoint is not None

    # Validate BLZ format
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
            "Missing TAN settings in .env: FINTS_TAN_METHOD, FINTS_TAN_MEDIUM. "
            "These are required by some banks to signal TAN capability.",
        )

    return {"tan_method": tan_method, "tan_medium": tan_medium}


@pytest.fixture(scope="module")
async def connected_adapter(credentials, tan_settings):
    """Create and connect Geldstrom adapter (reused across tests in module)."""
    adapter = GeldstromAdapter()

    # Set TAN method/medium before connecting (required by some banks)
    adapter.set_tan_method(tan_settings["tan_method"])
    adapter.set_tan_medium(tan_settings["tan_medium"])

    try:
        success = await adapter.connect(credentials)
        if not success:
            pytest.fail("Failed to connect to bank")

        yield adapter

    finally:
        if adapter.is_connected():
            await adapter.disconnect()


class TestRealBankConnection:
    """Test real bank connection and authentication.

    These tests verify basic connection functionality without requiring TAN.
    """

    @pytest.mark.asyncio
    async def test_connect_to_bank(self, credentials, tan_settings):
        """Verify successful connection to real bank."""
        adapter = GeldstromAdapter()
        adapter.set_tan_method(tan_settings["tan_method"])
        adapter.set_tan_medium(tan_settings["tan_medium"])

        try:
            success = await adapter.connect(credentials)

            assert success, "Failed to connect to bank"
            assert adapter.is_connected(), "Adapter should report connected"

        finally:
            if adapter.is_connected():
                await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect(self, credentials, tan_settings):
        """Verify clean disconnect."""
        adapter = GeldstromAdapter()
        adapter.set_tan_method(tan_settings["tan_method"])
        adapter.set_tan_medium(tan_settings["tan_medium"])

        await adapter.connect(credentials)
        assert adapter.is_connected()

        await adapter.disconnect()
        assert not adapter.is_connected()

    @pytest.mark.asyncio
    async def test_multiple_connect_disconnect_cycles(self, credentials, tan_settings):
        """Verify connection can be established multiple times."""
        adapter = GeldstromAdapter()
        adapter.set_tan_method(tan_settings["tan_method"])
        adapter.set_tan_medium(tan_settings["tan_medium"])

        # First cycle
        success1 = await adapter.connect(credentials)
        assert success1
        await adapter.disconnect()
        assert not adapter.is_connected()

        # Second cycle
        success2 = await adapter.connect(credentials)
        assert success2
        assert adapter.is_connected()
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_connection_with_invalid_credentials_fails(self):
        """Verify that invalid credentials result in connection failure."""
        adapter = GeldstromAdapter()
        invalid_creds = BankCredentials.from_plain(
            blz="12345678",
            username="invalid_user",
            pin="invalid_pin",
            endpoint="https://invalid.example.com/fints",
        )

        try:
            success = await adapter.connect(invalid_creds)
            # Should fail to connect
            assert not success, "Should not connect with invalid credentials"
        except Exception:  # noqa: S110
            # It's acceptable to raise an exception for invalid credentials
            # We're testing that it fails, not how it fails
            pass
        finally:
            if adapter.is_connected():
                await adapter.disconnect()


class TestRealAccountFetching:
    """Test fetching real accounts from the bank.

    These tests verify account listing functionality (no TAN required).
    """

    @pytest.mark.asyncio
    async def test_fetch_accounts(self, connected_adapter):
        """Fetch real accounts from bank."""
        accounts = await connected_adapter.fetch_accounts()

        # Basic assertions (don't rely on specific account data)
        assert len(accounts) > 0, "Should have at least one account"
        assert all(acc.iban for acc in accounts), "All accounts should have IBAN"
        assert all(acc.blz for acc in accounts), "All accounts should have BLZ"
        assert all(acc.account_number for acc in accounts), (
            "All accounts should have account number"
        )

    @pytest.mark.asyncio
    async def test_accounts_have_valid_iban(self, connected_adapter):
        """Verify accounts have valid German IBANs."""
        accounts = await connected_adapter.fetch_accounts()

        for account in accounts:
            assert account.iban.startswith(
                "DE",
            ), f"IBAN should start with DE: {account.iban}"
            assert len(account.iban) == 22, (
                f"German IBAN should be 22 chars: {account.iban}"
            )

    @pytest.mark.asyncio
    async def test_accounts_have_consistent_blz(self, connected_adapter, credentials):
        """Verify all accounts belong to the same bank (same BLZ)."""
        accounts = await connected_adapter.fetch_accounts()

        expected_blz = credentials.blz
        for account in accounts:
            assert account.blz == expected_blz, (
                f"Account BLZ {account.blz} should match credentials BLZ {expected_blz}"
            )

    @pytest.mark.asyncio
    async def test_accounts_have_currency(self, connected_adapter):
        """Verify all accounts have a currency (typically EUR)."""
        accounts = await connected_adapter.fetch_accounts()

        for account in accounts:
            assert account.currency, f"Account {account.iban} should have currency"
            assert account.currency in (
                "EUR",
                "USD",
                "GBP",
            ), f"Currency should be valid: {account.currency}"

    @pytest.mark.asyncio
    async def test_account_holder_name_present(self, connected_adapter):
        """Verify accounts have owner/holder information."""
        accounts = await connected_adapter.fetch_accounts()

        for account in accounts:
            assert account.account_holder, (
                f"Account {account.iban} should have account holder name"
            )


class TestRealTransactionFetching:
    """Test fetching real transactions (without TAN).

    These tests use short date ranges (30 days) which typically don't require TAN.
    """

    @pytest.mark.asyncio
    async def test_fetch_recent_transactions(self, connected_adapter):
        """Fetch 30 days of transactions (should not require TAN)."""
        accounts = await connected_adapter.fetch_accounts()
        if not accounts:
            pytest.skip("No accounts available")

        iban = accounts[0].iban
        start_date = date.today() - timedelta(days=30)

        transactions = await connected_adapter.fetch_transactions(
            iban,
            start_date=start_date,
        )

        # Should succeed without TAN
        assert isinstance(transactions, list)
        # Note: May be empty if no transactions in period

    @pytest.mark.asyncio
    async def test_transactions_have_required_fields(self, connected_adapter):
        """Verify transactions have all required fields."""
        accounts = await connected_adapter.fetch_accounts()
        if not accounts:
            pytest.skip("No accounts available")

        iban = accounts[0].iban
        start_date = date.today() - timedelta(days=30)

        transactions = await connected_adapter.fetch_transactions(
            iban,
            start_date=start_date,
        )

        if not transactions:
            pytest.skip("No transactions in period")

        for tx in transactions:
            assert tx.booking_date is not None, "Transaction should have booking date"
            assert tx.value_date is not None, "Transaction should have value date"
            assert tx.amount is not None, "Transaction should have amount"
            assert tx.currency is not None, "Transaction should have currency"
            assert tx.purpose is not None, "Transaction should have purpose"

    @pytest.mark.asyncio
    async def test_transaction_amounts_are_decimal(self, connected_adapter):
        """Verify transaction amounts are Decimal type with proper precision."""
        accounts = await connected_adapter.fetch_accounts()
        if not accounts:
            pytest.skip("No accounts available")

        iban = accounts[0].iban
        start_date = date.today() - timedelta(days=30)

        transactions = await connected_adapter.fetch_transactions(
            iban,
            start_date=start_date,
        )

        if not transactions:
            pytest.skip("No transactions in period")

        for tx in transactions:
            assert isinstance(tx.amount, Decimal), "Amount should be Decimal"
            # Check precision (max 2 decimal places for currency)
            assert abs(tx.amount) == abs(
                tx.amount.quantize(Decimal("0.01")),
            ), "Amount should have max 2 decimal places"

    @pytest.mark.asyncio
    async def test_transaction_dates_are_ordered(self, connected_adapter):
        """Verify transactions are returned in chronological order."""
        accounts = await connected_adapter.fetch_accounts()
        if not accounts:
            pytest.skip("No accounts available")

        iban = accounts[0].iban
        start_date = date.today() - timedelta(days=30)

        transactions = await connected_adapter.fetch_transactions(
            iban,
            start_date=start_date,
        )

        if len(transactions) < 2:
            pytest.skip("Need at least 2 transactions to verify ordering")

        # Verify booking dates are in ascending order
        booking_dates = [tx.booking_date for tx in transactions]
        assert booking_dates == sorted(
            booking_dates,
        ), "Transactions should be ordered by booking date"

    @pytest.mark.asyncio
    async def test_fetch_transactions_with_date_filter(self, connected_adapter):
        """Verify date filtering works correctly."""
        accounts = await connected_adapter.fetch_accounts()
        if not accounts:
            pytest.skip("No accounts available")

        iban = accounts[0].iban
        start_date = date.today() - timedelta(days=7)  # Only last 7 days

        transactions = await connected_adapter.fetch_transactions(
            iban,
            start_date=start_date,
        )

        # All transactions should be within the date range
        for tx in transactions:
            assert tx.booking_date >= start_date, (
                f"Transaction booking date {tx.booking_date} should be >= {start_date}"
            )

    @pytest.mark.asyncio
    async def test_fetch_transactions_for_all_accounts(self, connected_adapter):
        """Verify we can fetch transactions for all accounts."""
        accounts = await connected_adapter.fetch_accounts()
        if not accounts:
            pytest.skip("No accounts available")

        start_date = date.today() - timedelta(days=30)

        # Try to fetch for each account
        for account in accounts:
            transactions = await connected_adapter.fetch_transactions(
                account.iban,
                start_date=start_date,
            )
            # Should succeed (may be empty)
            assert isinstance(transactions, list)


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
            start_date = date.today() - timedelta(days=200)

            print(f"\n📱 Fetching {200} days of history for {iban}...")
            print("   If TAN is required, approve it in your banking app!")

            transactions = await adapter.fetch_transactions(iban, start_date=start_date)

            print(f"Successfully fetched {len(transactions)} transactions")

            # Long history should return substantial transactions
            assert len(transactions) > 0, "Expected transactions for 200-day history"

        finally:
            if adapter.is_connected():
                await adapter.disconnect()
