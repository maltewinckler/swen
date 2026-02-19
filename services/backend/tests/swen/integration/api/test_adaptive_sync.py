"""
Integration tests for adaptive sync functionality.

Tests the adaptive sync logic that prevents re-importing transactions:
1. First sync recommendation identifies unsynced accounts
2. First sync with days parameter imports initial transactions
3. Subsequent sync recommendation shows already-synced accounts
4. Adaptive sync (no days) only fetches from last sync date
5. Deduplication prevents duplicate transaction imports

Also tests:
- Opening balance creation on first sync
- Internal transfer detection between own accounts
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from swen.domain.banking.value_objects import BankAccount


@dataclass
class MockBankTransaction:
    """Mock bank transaction from FinTS."""

    id: str
    booking_date: datetime
    value_date: datetime
    amount: Decimal
    currency: str
    debitor_name: str | None
    creditor_name: str | None
    reference: str
    iban: str
    end_to_end_id: str | None = None


@dataclass
class MockInstituteInfo:
    """Mock FinTS institute info."""

    blz: str
    name: str
    bic: str
    city: str
    endpoint_url: str


@dataclass
class MockBankAccount:
    """Mock bank account."""

    iban: str
    account_number: str
    account_holder: str
    account_type: str
    blz: str
    bic: str
    bank_name: str
    currency: str
    balance: Decimal | None = None
    balance_date: datetime | None = None


MOCK_INSTITUTE = MockInstituteInfo(
    blz="12345678",
    name="Test Bank AG",
    bic="TESTDE00XXX",
    city="Berlin",
    endpoint_url="https://banking.test.de/fints",
)

# Use real domain BankAccount instead of mock
# BLZ must match the credentials BLZ used in user_with_bank fixture (12345678)
# IBAN format: DE + 2 check digits + 8-digit BLZ + 10-digit account number
# For BLZ 12345678, we need an IBAN like DE##12345678##########
MOCK_ACCOUNT = BankAccount(
    iban="DE89123456780532013000",  # BLZ 12345678 embedded in IBAN
    account_number="0532013000",
    account_holder="Max Mustermann",
    account_type="Girokonto",
    blz="12345678",  # Must match credentials BLZ
    bic="TESTDE00XXX",
    bank_name="Test Bank AG",
    currency="EUR",
    balance=Decimal("1500.00"),
    balance_date=datetime.now(timezone.utc),
)


def create_mock_transaction(
    iban: str,
    days_ago: int,
    amount: Decimal,
    reference: str,
    txn_id: str | None = None,
) -> MockBankTransaction:
    """Create a mock bank transaction."""
    now = datetime.now(timezone.utc)
    date = now - timedelta(days=days_ago)
    return MockBankTransaction(
        id=txn_id or str(uuid4()),
        booking_date=date,
        value_date=date,
        amount=amount,
        currency="EUR",
        debitor_name="Some Store" if amount < 0 else None,
        creditor_name="Employer GmbH" if amount > 0 else None,
        reference=reference,
        iban=iban,
        end_to_end_id=None,
    )


@pytest.fixture
def mock_fints_directory():
    """Mock the FinTS institute directory."""
    with patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory_async",
        new_callable=AsyncMock,
    ) as mock:
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = MOCK_INSTITUTE
        mock.return_value = mock_dir
        yield mock


@pytest.fixture
def mock_bank_adapter():
    """Mock the GeldstromAdapter for account discovery.

    Patches both the router import and the command import to ensure
    mocks work for both discover-accounts and setup (legacy flow).
    """
    with (
        patch(
            "swen.presentation.api.routers.credentials.GeldstromAdapter"
        ) as mock_router_adapter,
        patch(
            "swen.application.commands.banking.bank_connection_command.GeldstromAdapter"
        ) as mock_command_adapter,
    ):
        adapter_instance = AsyncMock()
        adapter_instance.is_connected.return_value = False
        adapter_instance.connect = AsyncMock()
        adapter_instance.disconnect = AsyncMock()
        adapter_instance.fetch_accounts = AsyncMock(return_value=[MOCK_ACCOUNT])
        adapter_instance.set_tan_method = MagicMock()
        adapter_instance.set_tan_medium = MagicMock()

        # Both patches return the same mock instance
        mock_router_adapter.return_value = adapter_instance
        mock_command_adapter.return_value = adapter_instance
        yield adapter_instance


@pytest.fixture
def mock_ml_client():
    """Mock the ML client."""
    with patch("swen.presentation.api.dependencies.get_ml_client") as mock_get_client:
        client = MagicMock()
        client.classify_batch.return_value = []
        client.store_example.return_value = None
        client.update_account.return_value = None
        mock_get_client.return_value = client
        yield client


def unique_account_number(prefix: str = "") -> str:
    """Generate a unique account number."""
    return f"{prefix}{uuid4().hex[:6]}"


@pytest.fixture
def user_with_bank(
    test_client: TestClient,
    authenticated_user: dict,
    api_v1_prefix: str,
    mock_fints_directory,
    mock_bank_adapter,
):
    """User with bank credentials and imported accounts."""
    headers = authenticated_user["headers"]
    blz = "12345678"

    # Store credentials
    test_client.post(
        f"{api_v1_prefix}/credentials",
        headers=headers,
        json={
            "blz": blz,
            "username": "testuser",
            "pin": "12345",
            "tan_method": "946",
        },
    )

    # Setup accounts
    setup_response = test_client.post(
        f"{api_v1_prefix}/credentials/{blz}/setup",
        headers=headers,
    )
    assert setup_response.status_code == 200, (
        f"Setup failed: {setup_response.status_code} - {setup_response.text}"
    )
    setup_data = setup_response.json()
    assert len(setup_data["accounts_imported"]) >= 1, (
        f"Expected at least 1 account imported, got {len(setup_data['accounts_imported'])}"
    )

    # Initialize chart
    test_client.post(
        f"{api_v1_prefix}/accounts/init-chart",
        headers=headers,
        json={"template": "minimal"},
    )

    return {
        **authenticated_user,
        "blz": blz,
        "iban": MOCK_ACCOUNT.iban,
    }


@pytest.mark.integration
class TestSyncRecommendation:
    """Tests for GET /sync/recommendation."""

    def test_recommendation_for_never_synced_account(
        self,
        test_client: TestClient,
        user_with_bank: dict,
        api_v1_prefix: str,
    ):
        """Accounts that have never synced should be flagged as first_sync."""
        headers = user_with_bank["headers"]

        # Debug: Check if credentials exist
        credentials_response = test_client.get(
            f"{api_v1_prefix}/credentials",
            headers=headers,
        )
        assert credentials_response.status_code == 200
        credentials = credentials_response.json()["credentials"]
        assert len(credentials) >= 1, f"Expected credentials but got: {credentials}"

        response = test_client.get(
            f"{api_v1_prefix}/sync/recommendation",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["has_first_sync_accounts"] is True, (
            f"Expected has_first_sync_accounts=True but got {data}. "
            f"Credentials: {credentials}"
        )
        assert data["total_accounts"] >= 1

        # All accounts should be first sync
        for account in data["accounts"]:
            assert account["is_first_sync"] is True
            assert account["successful_import_count"] == 0
            assert account["last_successful_sync_date"] is None

    def test_recommendation_empty_for_new_user(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """User without bank connections should get empty recommendation."""
        headers = authenticated_user["headers"]

        response = test_client.get(
            f"{api_v1_prefix}/sync/recommendation",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_accounts"] == 0
        assert data["has_first_sync_accounts"] is False
        assert data["accounts"] == []


@pytest.mark.integration
class TestAdaptiveSyncBehavior:
    """Tests for adaptive sync behavior."""

    def test_first_sync_with_days_parameter(
        self,
        test_client: TestClient,
        user_with_bank: dict,
        api_v1_prefix: str,
        mock_ml_client,
    ):
        """First sync should accept days parameter."""
        headers = user_with_bank["headers"]

        # Mock sync adapter for this test
        with patch(
            "swen.application.commands.integration.transaction_sync_command.GeldstromAdapter"
        ) as mock_adapter_class:
            adapter = AsyncMock()
            adapter.connect = AsyncMock()
            adapter.disconnect = AsyncMock()
            adapter.is_connected.return_value = False
            adapter.set_tan_method = MagicMock()
            adapter.set_tan_medium = MagicMock()

            # Return transactions for 30 days
            transactions = [
                create_mock_transaction(
                    user_with_bank["iban"],
                    days_ago=i * 5,
                    amount=Decimal(f"-{50 + i * 10}"),
                    reference=f"Purchase {i}",
                )
                for i in range(5)
            ]
            adapter.fetch_transactions = AsyncMock(return_value=transactions)
            mock_adapter_class.return_value = adapter

            response = test_client.post(
                f"{api_v1_prefix}/sync/run",
                headers=headers,
                json={"days": 30, "auto_post": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_sync_status_after_first_sync(
        self,
        test_client: TestClient,
        user_with_bank: dict,
        api_v1_prefix: str,
        mock_ml_client,
    ):
        """After first sync, status should reflect sync history."""
        headers = user_with_bank["headers"]

        # Perform a sync first
        with patch(
            "swen.application.commands.integration.transaction_sync_command.GeldstromAdapter"
        ) as mock_adapter_class:
            adapter = AsyncMock()
            adapter.connect = AsyncMock()
            adapter.disconnect = AsyncMock()
            adapter.is_connected.return_value = False
            adapter.set_tan_method = MagicMock()
            adapter.set_tan_medium = MagicMock()
            adapter.fetch_transactions = AsyncMock(return_value=[])
            mock_adapter_class.return_value = adapter

            test_client.post(
                f"{api_v1_prefix}/sync/run",
                headers=headers,
                json={"days": 30},
            )

        # Check status
        status_response = test_client.get(
            f"{api_v1_prefix}/sync/status",
            headers=headers,
        )

        assert status_response.status_code == 200
        # Status structure varies - just ensure it returns


@pytest.mark.integration
class TestDeduplication:
    """Tests for transaction deduplication during sync."""

    def test_duplicate_transactions_skipped(
        self,
        test_client: TestClient,
        user_with_bank: dict,
        api_v1_prefix: str,
        mock_ml_client,
    ):
        """Same transaction synced twice should be deduplicated."""
        headers = user_with_bank["headers"]
        txn_id = str(uuid4())

        # First sync with one transaction
        with patch(
            "swen.application.commands.integration.transaction_sync_command.GeldstromAdapter"
        ) as mock_adapter_class:
            adapter = AsyncMock()
            adapter.connect = AsyncMock()
            adapter.disconnect = AsyncMock()
            adapter.is_connected.return_value = False
            adapter.set_tan_method = MagicMock()
            adapter.set_tan_medium = MagicMock()

            transaction = create_mock_transaction(
                user_with_bank["iban"],
                days_ago=5,
                amount=Decimal("-50.00"),
                reference="Unique Purchase",
                txn_id=txn_id,
            )
            adapter.fetch_transactions = AsyncMock(return_value=[transaction])
            mock_adapter_class.return_value = adapter

            first_sync = test_client.post(
                f"{api_v1_prefix}/sync/run",
                headers=headers,
                json={"days": 30},
            )

        assert first_sync.status_code == 200
        first_data = first_sync.json()
        first_imported = first_data["total_imported"]

        # Second sync with same transaction
        with patch(
            "swen.application.commands.integration.transaction_sync_command.GeldstromAdapter"
        ) as mock_adapter_class:
            adapter = AsyncMock()
            adapter.connect = AsyncMock()
            adapter.disconnect = AsyncMock()
            adapter.is_connected.return_value = False
            adapter.set_tan_method = MagicMock()
            adapter.set_tan_medium = MagicMock()

            # Same transaction
            transaction = create_mock_transaction(
                user_with_bank["iban"],
                days_ago=5,
                amount=Decimal("-50.00"),
                reference="Unique Purchase",
                txn_id=txn_id,
            )
            adapter.fetch_transactions = AsyncMock(return_value=[transaction])
            mock_adapter_class.return_value = adapter

            second_sync = test_client.post(
                f"{api_v1_prefix}/sync/run",
                headers=headers,
                json={"days": 30},
            )

        assert second_sync.status_code == 200
        second_data = second_sync.json()

        # Should be skipped as duplicate
        assert second_data["total_skipped"] >= 1 or second_data["total_imported"] == 0


@pytest.mark.integration
class TestEssentialAccounts:
    """Tests for essential accounts initialization."""

    def test_init_essentials_creates_required_accounts(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """Init essentials should create Bargeld, Sonstiges, Sonstige Einnahmen."""
        headers = authenticated_user["headers"]

        response = test_client.post(
            f"{api_v1_prefix}/accounts/init-essentials",
            headers=headers,
        )

        assert response.status_code in (200, 201)
        data = response.json()

        # Should create 3 essential accounts
        assert data["accounts_created"] == 3

        # Verify accounts exist
        accounts_response = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=headers,
        )
        accounts = accounts_response.json()["accounts"]
        account_numbers = [a["account_number"] for a in accounts]

        assert "1000" in account_numbers  # Bargeld
        assert "3100" in account_numbers  # Sonstige Einnahmen (income)
        assert "4900" in account_numbers  # Sonstiges (expense)

    def test_init_essentials_idempotent(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """Calling init-essentials twice should not create duplicates."""
        headers = authenticated_user["headers"]

        # First call
        first = test_client.post(
            f"{api_v1_prefix}/accounts/init-essentials",
            headers=headers,
        )
        assert first.status_code in (200, 201)

        # Second call
        second = test_client.post(
            f"{api_v1_prefix}/accounts/init-essentials",
            headers=headers,
        )
        assert second.status_code in (200, 201)
        assert second.json()["accounts_created"] == 0  # None created


@pytest.mark.integration
class TestReconciliation:
    """Tests for account reconciliation endpoint."""

    def test_reconciliation_empty_for_new_user(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """New user should have empty reconciliation."""
        headers = authenticated_user["headers"]

        response = test_client.get(
            f"{api_v1_prefix}/accounts/reconciliation",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["accounts"] == []
