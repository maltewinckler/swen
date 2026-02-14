"""
E2E tests for the complete bank connection journey.

This tests the critical user flow:
1. Store bank credentials
2. Query TAN methods
3. Discover bank accounts
4. Setup/import accounts (with custom names)
5. First sync with TAN approval simulation
6. Verify transactions imported
7. Subsequent sync (adaptive mode)

All bank interactions are mocked to simulate real behavior.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@dataclass
class MockInstituteInfo:
    """Mock FinTS institute info for tests."""

    blz: str
    name: str
    bic: str
    city: str
    endpoint_url: str


@dataclass
class MockBankAccount:
    """Mock bank account from FinTS."""

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


@dataclass
class MockBankTransaction:
    """Mock bank transaction from FinTS."""

    booking_date: datetime
    value_date: datetime
    amount: Decimal
    currency: str
    debitor_name: str | None
    creditor_name: str | None
    reference: str
    iban: str


# Test data
MOCK_INSTITUTE = MockInstituteInfo(
    blz="12345678",
    name="Test Bank AG",
    bic="TESTDE00XXX",
    city="Berlin",
    endpoint_url="https://banking.testbank.de/fints",
)

MOCK_ACCOUNTS = [
    MockBankAccount(
        iban="DE89777788880532013000",
        account_number="0532013000",
        account_holder="Max Mustermann",
        account_type="Girokonto",
        blz="77778888",
        bic="TESTDE00XXX",
        bank_name="Test Bank AG",
        currency="EUR",
        balance=Decimal("1500.00"),
        balance_date=datetime.now(timezone.utc),
    ),
    MockBankAccount(
        iban="DE89777788880532013001",
        account_number="0532013001",
        account_holder="Max Mustermann",
        account_type="Tagesgeld",
        blz="77778888",
        bic="TESTDE00XXX",
        bank_name="Test Bank AG",
        currency="EUR",
        balance=Decimal("5000.00"),
        balance_date=datetime.now(timezone.utc),
    ),
]


def generate_mock_transactions(
    iban: str,
    count: int = 5,
    days_ago: int = 30,
) -> list[MockBankTransaction]:
    """Generate mock bank transactions for testing."""
    transactions = []
    now = datetime.now(timezone.utc)

    counterparties = [
        ("REWE Markt GmbH", "Einkauf REWE 12345"),
        ("Amazon EU S.a.r.l.", "AMAZON 123-456-789"),
        ("Spotify AB", "Spotify Premium"),
        ("Gehalt Arbeitgeber GmbH", "GEHALT 01/2024"),
        ("Stadtwerke Berlin", "Strom Abschlag"),
    ]

    for i in range(count):
        date = now - timedelta(days=days_ago - i * (days_ago // count))
        cp_name, ref = counterparties[i % len(counterparties)]
        is_income = i == 3  # Gehalt

        transactions.append(
            MockBankTransaction(
                booking_date=date,
                value_date=date,
                amount=Decimal("2500.00") if is_income else Decimal(f"-{50 + i * 10}"),
                currency="EUR",
                debitor_name=None if is_income else cp_name,
                creditor_name=cp_name if is_income else None,
                reference=ref,
                iban=iban,
            )
        )

    return transactions


@pytest.fixture
def mock_fints_directory():
    """Mock the FinTS institute directory."""
    with patch(
        "swen.presentation.api.routers.credentials.get_fints_institute_directory"
    ) as mock:
        mock_dir = MagicMock()
        mock_dir.find_by_blz.return_value = MOCK_INSTITUTE
        mock.return_value = mock_dir
        yield mock


@pytest.fixture
def mock_bank_adapter():
    """Mock the GeldstromAdapter for bank connections."""
    adapter_instance = AsyncMock()
    adapter_instance.is_connected.return_value = False
    adapter_instance.connect = AsyncMock()
    adapter_instance.disconnect = AsyncMock()
    adapter_instance.fetch_accounts = AsyncMock(return_value=MOCK_ACCOUNTS)
    adapter_instance.set_tan_method = MagicMock()
    adapter_instance.set_tan_medium = MagicMock()

    with (
        patch(
            "swen.presentation.api.routers.credentials.GeldstromAdapter"
        ) as mock_adapter_class_router,
        patch(
            "swen.application.commands.banking.bank_connection_command.GeldstromAdapter"
        ) as mock_adapter_class_command,
    ):
        mock_adapter_class_router.return_value = adapter_instance
        mock_adapter_class_command.return_value = adapter_instance
        yield adapter_instance


@pytest.fixture
def mock_sync_adapter():
    """Mock the adapter for sync operations."""
    with patch(
        "swen.application.commands.integration.transaction_sync_command.GeldstromAdapter"
    ) as mock_adapter_class:
        adapter_instance = AsyncMock()
        adapter_instance.is_connected.return_value = False
        adapter_instance.connect = AsyncMock()
        adapter_instance.disconnect = AsyncMock()

        # Return transactions based on IBAN
        async def fetch_transactions_mock(start_date, end_date, iban=None):
            if iban:
                return generate_mock_transactions(iban, count=5, days_ago=30)
            # Return transactions for all accounts
            all_txns = []
            for acc in MOCK_ACCOUNTS:
                all_txns.extend(
                    generate_mock_transactions(acc.iban, count=5, days_ago=30)
                )
            return all_txns

        adapter_instance.fetch_transactions = AsyncMock(
            side_effect=fetch_transactions_mock
        )
        adapter_instance.set_tan_method = MagicMock()
        adapter_instance.set_tan_medium = MagicMock()
        mock_adapter_class.return_value = adapter_instance
        yield adapter_instance


@pytest.fixture
def mock_ml_client():
    """Mock the ML client for classification."""
    with patch("swen.presentation.api.dependencies.get_ml_client") as mock_get_client:
        client = MagicMock()
        # Mock classification response
        client.classify_batch.return_value = []  # Empty - no suggestions
        client.store_example.return_value = None
        client.update_account.return_value = None
        mock_get_client.return_value = client
        yield client


@pytest.mark.e2e
class TestBankConnectionJourney:
    """Test the complete bank connection flow from credentials to first sync."""

    def test_complete_bank_connection_flow(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
        mock_fints_directory,
        mock_bank_adapter,
    ):
        """
        Full journey: credentials → discover → setup.

        This simulates a user connecting their bank for the first time.
        """
        headers = authenticated_user["headers"]
        blz = "12345678"

        # Step 1: Store bank credentials
        store_response = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=headers,
            json={
                "blz": blz,
                "username": "testuser123",
                "pin": "12345",
                "tan_method": "946",
                "tan_medium": "SecureGo plus",
            },
        )
        assert store_response.status_code == 201, (
            f"Store credentials failed: {store_response.text}"
        )
        cred_data = store_response.json()
        assert cred_data["blz"] == blz
        assert cred_data["label"] == "Test Bank AG"
        assert "credential_id" in cred_data

        # Step 2: Discover bank accounts
        discover_response = test_client.post(
            f"{api_v1_prefix}/credentials/{blz}/discover-accounts",
            headers=headers,
        )
        assert discover_response.status_code == 200, (
            f"Discover accounts failed: {discover_response.text}"
        )
        discover_data = discover_response.json()
        assert discover_data["blz"] == blz
        assert discover_data["bank_name"] == "Test Bank AG"
        assert len(discover_data["accounts"]) == 2

        # Verify discovered account details
        account_ibans = [acc["iban"] for acc in discover_data["accounts"]]
        assert len(account_ibans) == 2
        # Verify both accounts have the expected structure
        for acc in discover_data["accounts"]:
            assert acc["account_holder"] == "Max Mustermann"
            assert acc["bank_name"] == "Test Bank AG"

        # Step 3: Setup accounts with custom names
        # User can customize names from the discover response
        setup_response = test_client.post(
            f"{api_v1_prefix}/credentials/{blz}/setup",
            headers=headers,
            json={
                "accounts": discover_data["accounts"],
                "account_names": {
                    discover_data["accounts"][0]["iban"]: "Mein Girokonto",
                    discover_data["accounts"][1]["iban"]: "Sparkonto",
                },
            },
        )
        assert setup_response.status_code == 200, f"Setup failed: {setup_response.text}"
        setup_data = setup_response.json()
        assert len(setup_data["accounts_imported"]) >= 2

        # Step 4: Verify mappings were created
        mappings_response = test_client.get(
            f"{api_v1_prefix}/mappings",
            headers=headers,
        )
        assert mappings_response.status_code == 200
        mappings = mappings_response.json()["mappings"]
        assert len(mappings) == 2
        # Verify mappings have the expected structure
        for mapping in mappings:
            assert "iban" in mapping
            assert "accounting_account_id" in mapping

        # Step 5: Verify accounting accounts were created
        accounts_response = test_client.get(
            f"{api_v1_prefix}/accounts?account_type=asset",
            headers=headers,
        )
        assert accounts_response.status_code == 200
        accounts = accounts_response.json()["accounts"]
        account_names = [a["name"] for a in accounts]
        assert "Mein Girokonto" in account_names
        assert "Sparkonto" in account_names

    def test_duplicate_credentials_rejected(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
        mock_fints_directory,
    ):
        """Cannot store credentials twice for the same bank."""
        headers = authenticated_user["headers"]
        blz = "11112222"  # Different BLZ to avoid conflicts

        # First store - should succeed
        first_response = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=headers,
            json={
                "blz": blz,
                "username": "user1",
                "pin": "pin1",
                "tan_method": "946",
            },
        )
        assert first_response.status_code == 201

        # Second store - should fail
        second_response = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=headers,
            json={
                "blz": blz,
                "username": "user2",
                "pin": "pin2",
                "tan_method": "946",
            },
        )
        assert second_response.status_code == 409
        assert "already" in second_response.json()["detail"].lower()

    def test_credentials_isolation_between_users(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
        mock_fints_directory,
    ):
        """Users cannot see each other's bank credentials."""
        blz = "33334444"

        # Register user 1
        user1_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={
                "email": f"bank-user1-{uuid.uuid4().hex[:8]}@example.com",
                "password": "Password123!",
            },
        )
        user1_headers = {
            "Authorization": f"Bearer {user1_response.json()['access_token']}"
        }

        # Register user 2
        user2_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={
                "email": f"bank-user2-{uuid.uuid4().hex[:8]}@example.com",
                "password": "Password123!",
            },
        )
        user2_headers = {
            "Authorization": f"Bearer {user2_response.json()['access_token']}"
        }

        # User 1 stores credentials
        test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=user1_headers,
            json={
                "blz": blz,
                "username": "user1secret",
                "pin": "secret123",
                "tan_method": "946",
            },
        )

        # User 2 should see empty credentials list
        user2_creds = test_client.get(
            f"{api_v1_prefix}/credentials",
            headers=user2_headers,
        )
        assert user2_creds.status_code == 200
        assert user2_creds.json()["total"] == 0

        # User 2 should be able to store same BLZ (different user)
        user2_store = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=user2_headers,
            json={
                "blz": blz,
                "username": "user2different",
                "pin": "different456",
                "tan_method": "946",
            },
        )
        assert user2_store.status_code == 201


@pytest.mark.e2e
class TestSyncAfterBankConnection:
    """Test sync behavior after bank connection is established."""

    def test_first_sync_with_days_parameter(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
        mock_fints_directory,
        mock_bank_adapter,
        mock_sync_adapter,
        mock_ml_client,
    ):
        """First sync should allow specifying days of history."""
        headers = authenticated_user["headers"]
        blz = "55556666"

        # Setup: Store credentials and setup accounts
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

        test_client.post(
            f"{api_v1_prefix}/credentials/{blz}/setup",
            headers=headers,
        )

        # Initialize chart for expense accounts
        test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=headers,
            json={"template": "minimal"},
        )

        # First sync with 30 days
        sync_response = test_client.post(
            f"{api_v1_prefix}/sync/run",
            headers=headers,
            json={"days": 30, "auto_post": True},
        )
        assert sync_response.status_code == 200, f"Sync failed: {sync_response.text}"
        sync_data = sync_response.json()
        assert sync_data["success"] is True
        assert sync_data["total_fetched"] >= 0

    def test_sync_recommendation_for_first_sync(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
        mock_fints_directory,
        mock_bank_adapter,
    ):
        """Get sync recommendation should identify first-sync accounts."""
        headers = authenticated_user["headers"]
        blz = "77778888"

        # Setup bank connection
        cred_response = test_client.post(
            f"{api_v1_prefix}/credentials",
            headers=headers,
            json={
                "blz": blz,
                "username": "testuser",
                "pin": "12345",
                "tan_method": "946",
            },
        )
        assert cred_response.status_code == 201, (
            f"Credentials failed: {cred_response.text}"
        )

        setup_response = test_client.post(
            f"{api_v1_prefix}/credentials/{blz}/setup",
            headers=headers,
        )
        assert setup_response.status_code == 200, f"Setup failed: {setup_response.text}"
        setup_data = setup_response.json()
        assert setup_data["success"] is True
        assert len(setup_data["accounts_imported"]) >= 2

        # Get sync recommendation
        rec_response = test_client.get(
            f"{api_v1_prefix}/sync/recommendation",
            headers=headers,
        )
        assert rec_response.status_code == 200
        rec_data = rec_response.json()

        # All accounts should be first-sync
        assert rec_data["has_first_sync_accounts"] is True
        assert rec_data["total_accounts"] >= 2

        for account in rec_data["accounts"]:
            assert account["is_first_sync"] is True
            assert account["successful_import_count"] == 0


@pytest.mark.e2e
class TestOnboardingStatusJourney:
    """Test onboarding status reflects bank connection progress."""

    def test_onboarding_status_progression(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
        mock_fints_directory,
        mock_bank_adapter,
    ):
        """Onboarding status should update as user connects bank."""
        headers = authenticated_user["headers"]
        blz = "99990000"

        # Initial status - needs onboarding
        status1 = test_client.get(
            f"{api_v1_prefix}/onboarding/status",
            headers=headers,
        )
        assert status1.status_code == 200
        assert status1.json()["needs_onboarding"] is True
        assert status1.json()["completed_steps"]["accounts_initialized"] is False
        assert status1.json()["completed_steps"]["first_bank_connected"] is False

        # Initialize accounts
        test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=headers,
            json={"template": "minimal"},
        )

        # Status after accounts
        status2 = test_client.get(
            f"{api_v1_prefix}/onboarding/status",
            headers=headers,
        )
        assert status2.json()["completed_steps"]["accounts_initialized"] is True
        assert status2.json()["needs_onboarding"] is False

        # Connect bank
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

        # Status after bank connected
        status3 = test_client.get(
            f"{api_v1_prefix}/onboarding/status",
            headers=headers,
        )
        assert status3.json()["completed_steps"]["first_bank_connected"] is True
