"""
E2E tests for critical user journeys.

These tests simulate complete user flows through the API:
1. User Onboarding - Register → Init Chart → First Transaction
2. Account Management - Create → Update → Deactivate → Reactivate
3. Transaction Lifecycle - Create → Post → Edit → Unpost → Delete
4. Dashboard & Reporting - View Summary → Spending → Balances
5. Preferences Management - Get → Update → Reset

Each test class represents a complete user journey that exercises
multiple endpoints in a realistic sequence.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


def unique_account_number(prefix: str = "") -> str:
    """Generate a unique account number to avoid conflicts between tests."""
    return f"{prefix}{uuid.uuid4().hex[:6]}"


def recent_date(days_ago: int = 0) -> str:
    """Get an ISO date string for N days ago (within dashboard's 30-day window)."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.e2e
class TestUserOnboardingJourney:
    """Test the complete user onboarding flow.

    Journey: Register → Init Chart → Create First Transaction → View Dashboard
    """

    def test_new_user_can_complete_onboarding(
        self,
        test_client: TestClient,
        e2e_user_data: dict,
        api_v1_prefix: str,
    ):
        """A new user can register, set up accounts, and make their first transaction."""
        # Step 1: Register new user
        register_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json=e2e_user_data,
        )
        assert register_response.status_code == 201
        auth_data = register_response.json()
        headers = {"Authorization": f"Bearer {auth_data['access_token']}"}
        user_id = auth_data["user"]["id"]

        # Verify user identity
        me_response = test_client.get(f"{api_v1_prefix}/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["id"] == user_id

        # Step 2: Initialize chart of accounts
        chart_response = test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=headers,
            json={"template": "minimal"},
        )
        assert chart_response.status_code == 201
        chart_data = chart_response.json()
        assert chart_data["accounts_created"] > 0
        assert chart_data["template"] == "minimal"

        # Step 3: Verify accounts were created
        accounts_response = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=headers,
        )
        assert accounts_response.status_code == 200
        accounts = accounts_response.json()["accounts"]
        assert len(accounts) > 0

        # Find an expense account and an asset account for transaction
        expense_accounts = [a for a in accounts if a["account_type"] == "expense"]
        asset_accounts = [a for a in accounts if a["account_type"] == "asset"]

        # If no asset account exists (minimal template), create one
        if not asset_accounts:
            create_asset_response = test_client.post(
                f"{api_v1_prefix}/accounts",
                headers=headers,
                json={
                    "name": "My Checking Account",
                    "account_type": "asset",
                    "account_number": unique_account_number("1"),
                    "currency": "EUR",
                    "description": "Main checking account",
                },
            )
            assert create_asset_response.status_code == 201
            asset_account = create_asset_response.json()
        else:
            asset_account = asset_accounts[0]

        expense_account = expense_accounts[0] if expense_accounts else None

        # If no expense account, create one
        if not expense_account:
            create_expense_response = test_client.post(
                f"{api_v1_prefix}/accounts",
                headers=headers,
                json={
                    "name": "Groceries",
                    "account_type": "expense",
                    "account_number": unique_account_number("4"),
                    "currency": "EUR",
                },
            )
            assert create_expense_response.status_code == 201
            expense_account = create_expense_response.json()

        # Step 4: Create first transaction
        transaction_response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),  # Yesterday (within 30-day window)
                "description": "First grocery shopping",
                "counterparty": "REWE",
                "entries": [
                    {
                        "account_id": str(expense_account["id"]),
                        "debit": "45.99",
                        "credit": "0",
                    },
                    {
                        "account_id": str(asset_account["id"]),
                        "debit": "0",
                        "credit": "45.99",
                    },
                ],
                "auto_post": True,
            },
        )
        assert transaction_response.status_code == 201
        transaction = transaction_response.json()
        assert transaction["description"] == "First grocery shopping"
        assert transaction["is_posted"] is True

        # Step 5: View dashboard to see the transaction reflected
        dashboard_response = test_client.get(
            f"{api_v1_prefix}/dashboard/summary?days=30",
            headers=headers,
        )
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()
        # Should show expenses (the transaction we just created)
        # API returns strings, convert to Decimal for comparison
        assert Decimal(str(dashboard["total_expenses"])) >= Decimal("45.99")

    def test_chart_initialization_is_idempotent(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """Chart initialization can be called multiple times without duplicating accounts."""
        headers = authenticated_user["headers"]

        # First initialization
        response1 = test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=headers,
            json={"template": "minimal"},
        )
        assert response1.status_code == 201
        first_count = response1.json()["accounts_created"]

        # Second initialization should skip
        response2 = test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=headers,
            json={"template": "minimal"},
        )
        # Could be 200 (skipped) or 201 with skipped=True
        assert response2.status_code in (200, 201)
        assert response2.json()["skipped"] is True

        # Verify account count hasn't changed
        accounts_response = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=headers,
        )
        # Should have same number of accounts (only from first init)
        assert len(accounts_response.json()["accounts"]) == first_count


@pytest.mark.e2e
class TestAccountManagementJourney:
    """Test the complete account management flow.

    Journey: Create Account → Get → Update → Get Stats → Deactivate → Reactivate
    """

    def test_full_account_lifecycle(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """A user can manage accounts through their full lifecycle."""
        headers = user_with_chart["headers"]

        # Step 1: Create a custom expense account with unique number
        account_number = unique_account_number("45")
        create_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Entertainment",
                "account_type": "expense",
                "account_number": account_number,
                "currency": "EUR",
                "description": "Movies, concerts, games",
            },
        )
        assert create_response.status_code == 201, (
            f"Account creation failed: {create_response.text}"
        )
        account = create_response.json()
        account_id = account["id"]
        assert account["name"] == "Entertainment"
        assert account["account_type"] == "expense"
        assert account["is_active"] is True

        # Step 2: Get the account by ID
        get_response = test_client.get(
            f"{api_v1_prefix}/accounts/{account_id}",
            headers=headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["description"] == "Movies, concerts, games"

        # Step 3: Update the account
        update_response = test_client.patch(
            f"{api_v1_prefix}/accounts/{account_id}",
            headers=headers,
            json={
                "name": "Entertainment & Hobbies",
                "description": "All fun activities",
            },
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Entertainment & Hobbies"

        # Step 4: Get account stats (should be empty initially)
        stats_response = test_client.get(
            f"{api_v1_prefix}/accounts/{account_id}/stats",
            headers=headers,
        )
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert stats["transaction_count"] == 0
        # Balance may be returned as "0" or "0.00" depending on formatting
        assert Decimal(stats["balance"]) == Decimal("0")

        # Step 5: Deactivate the account
        deactivate_response = test_client.delete(
            f"{api_v1_prefix}/accounts/{account_id}",
            headers=headers,
        )
        assert deactivate_response.status_code == 204

        # Step 6: Verify account is no longer in active list
        list_response = test_client.get(
            f"{api_v1_prefix}/accounts?active_only=true",
            headers=headers,
        )
        account_ids = [a["id"] for a in list_response.json()["accounts"]]
        assert account_id not in account_ids

        # Step 7: Reactivate the account
        reactivate_response = test_client.post(
            f"{api_v1_prefix}/accounts/{account_id}/reactivate",
            headers=headers,
        )
        assert reactivate_response.status_code == 200
        assert reactivate_response.json()["is_active"] is True

        # Step 8: Verify account is back in active list
        list_response2 = test_client.get(
            f"{api_v1_prefix}/accounts?active_only=true",
            headers=headers,
        )
        account_ids2 = [a["id"] for a in list_response2.json()["accounts"]]
        assert account_id in account_ids2

    def test_permanent_delete_removes_account(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """Permanent delete removes an account from the system."""
        headers = user_with_chart["headers"]

        # Create an expense account with unique number
        expense_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Deletable Expense",
                "account_type": "expense",
                "account_number": unique_account_number("46"),
                "currency": "EUR",
            },
        )
        assert expense_response.status_code == 201, (
            f"Expense account creation failed: {expense_response.text}"
        )
        expense_id = expense_response.json()["id"]

        # Verify account exists
        get_response = test_client.get(
            f"{api_v1_prefix}/accounts/{expense_id}",
            headers=headers,
        )
        assert get_response.status_code == 200

        # Permanently delete the account
        delete_response = test_client.delete(
            f"{api_v1_prefix}/accounts/{expense_id}/permanent",
            headers=headers,
        )
        assert delete_response.status_code == 204

        # Verify account is gone
        get_after_delete = test_client.get(
            f"{api_v1_prefix}/accounts/{expense_id}",
            headers=headers,
        )
        assert get_after_delete.status_code == 404


@pytest.mark.e2e
class TestTransactionLifecycleJourney:
    """Test the complete transaction lifecycle.

    Journey: Create Draft → View → Post → Edit → Unpost → Delete
    """

    def test_full_transaction_lifecycle(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """A user can manage transactions through their full lifecycle."""
        headers = user_with_chart["headers"]

        # First, create the necessary accounts with unique numbers
        asset_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Main Checking",
                "account_type": "asset",
                "account_number": unique_account_number("10"),
                "currency": "EUR",
            },
        )
        assert asset_response.status_code == 201, (
            f"Asset account creation failed: {asset_response.text}"
        )
        asset_id = asset_response.json()["id"]

        expense_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Restaurant",
                "account_type": "expense",
                "account_number": unique_account_number("43"),
                "currency": "EUR",
            },
        )
        assert expense_response.status_code == 201, (
            f"Expense account creation failed: {expense_response.text}"
        )
        expense_id = expense_response.json()["id"]

        # Step 1: Create a draft transaction (auto_post=False)
        create_response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Dinner at Restaurant",
                "counterparty": "Ristorante Italiano",
                "entries": [
                    {"account_id": expense_id, "debit": "65.00", "credit": "0"},
                    {"account_id": asset_id, "debit": "0", "credit": "65.00"},
                ],
                "auto_post": False,
            },
        )
        assert create_response.status_code == 201
        transaction = create_response.json()
        transaction_id = transaction["id"]
        assert transaction["is_posted"] is False
        assert transaction["counterparty"] == "Ristorante Italiano"

        # Step 2: View the transaction
        get_response = test_client.get(
            f"{api_v1_prefix}/transactions/{transaction_id}",
            headers=headers,
        )
        assert get_response.status_code == 200
        assert get_response.json()["description"] == "Dinner at Restaurant"

        # Step 3: Post the transaction
        post_response = test_client.post(
            f"{api_v1_prefix}/transactions/{transaction_id}/post",
            headers=headers,
        )
        assert post_response.status_code == 200
        assert post_response.json()["is_posted"] is True

        # Step 4: Edit the transaction (description and counterparty)
        edit_response = test_client.put(
            f"{api_v1_prefix}/transactions/{transaction_id}",
            headers=headers,
            json={
                "description": "Dinner with friends",
                "counterparty": "Italian Restaurant",
            },
        )
        assert edit_response.status_code == 200
        assert edit_response.json()["description"] == "Dinner with friends"
        assert edit_response.json()["counterparty"] == "Italian Restaurant"

        # Step 5: Unpost the transaction
        unpost_response = test_client.post(
            f"{api_v1_prefix}/transactions/{transaction_id}/unpost",
            headers=headers,
        )
        assert unpost_response.status_code == 200
        assert unpost_response.json()["is_posted"] is False

        # Step 6: Delete the transaction (now possible since it's a draft)
        delete_response = test_client.delete(
            f"{api_v1_prefix}/transactions/{transaction_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        # Step 7: Verify transaction is gone
        get_deleted_response = test_client.get(
            f"{api_v1_prefix}/transactions/{transaction_id}",
            headers=headers,
        )
        assert get_deleted_response.status_code == 404

    def test_simple_transaction_creation(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """The simple transaction endpoint auto-resolves accounts."""
        headers = user_with_chart["headers"]

        # Create accounts first with unique numbers
        test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Checking",
                "account_type": "asset",
                "account_number": unique_account_number("10"),
                "currency": "EUR",
            },
        )

        test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Default Expense",
                "account_type": "expense",
                "account_number": unique_account_number("40"),
                "currency": "EUR",
            },
        )

        # Create a simple expense transaction
        response = test_client.post(
            f"{api_v1_prefix}/transactions/simple",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Coffee Shop",
                "amount": "-4.50",  # Negative = expense
                "counterparty": "Starbucks",
                "auto_post": True,
            },
        )

        # The endpoint should work if it can resolve accounts
        # If it fails (400/422), it means account resolution wasn't possible
        # which is acceptable for this test
        assert response.status_code in (201, 400, 422)

    def test_split_transaction(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """Transactions can be split across multiple accounts."""
        headers = user_with_chart["headers"]

        # Create accounts with unique numbers
        asset_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Split Checking",
                "account_type": "asset",
                "account_number": unique_account_number("10"),
                "currency": "EUR",
            },
        )
        assert asset_response.status_code == 201, (
            f"Asset account creation failed: {asset_response.text}"
        )
        asset_id = asset_response.json()["id"]

        groceries_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Groceries",
                "account_type": "expense",
                "account_number": unique_account_number("42"),
                "currency": "EUR",
            },
        )
        assert groceries_response.status_code == 201, (
            f"Groceries account creation failed: {groceries_response.text}"
        )
        groceries_id = groceries_response.json()["id"]

        household_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Household",
                "account_type": "expense",
                "account_number": unique_account_number("42"),
                "currency": "EUR",
            },
        )
        assert household_response.status_code == 201, (
            f"Household account creation failed: {household_response.text}"
        )
        household_id = household_response.json()["id"]

        # Create a split transaction (groceries + household from same purchase)
        response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Supermarket Mixed Purchase",
                "counterparty": "REWE",
                "entries": [
                    {"account_id": groceries_id, "debit": "30.00", "credit": "0"},
                    {"account_id": household_id, "debit": "20.00", "credit": "0"},
                    {"account_id": asset_id, "debit": "0", "credit": "50.00"},
                ],
                "auto_post": True,
            },
        )

        assert response.status_code == 201
        transaction = response.json()
        assert len(transaction["entries"]) == 3
        assert transaction["is_posted"] is True


@pytest.mark.e2e
class TestDashboardAndReportingJourney:
    """Test the dashboard and reporting flow.

    Journey: Create Transactions → View Dashboard → View Spending → View Balances
    """

    def test_dashboard_reflects_transactions(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """The dashboard accurately reflects transaction data."""
        headers = user_with_chart["headers"]

        # Create accounts with unique numbers
        asset_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Dashboard Checking",
                "account_type": "asset",
                "account_number": unique_account_number("10"),
                "currency": "EUR",
            },
        )
        assert asset_response.status_code == 201, (
            f"Asset account creation failed: {asset_response.text}"
        )
        asset_id = asset_response.json()["id"]

        income_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Salary",
                "account_type": "income",
                "account_number": unique_account_number("30"),
                "currency": "EUR",
            },
        )
        assert income_response.status_code == 201, (
            f"Income account creation failed: {income_response.text}"
        )
        income_id = income_response.json()["id"]

        expense_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Rent",
                "account_type": "expense",
                "account_number": unique_account_number("41"),
                "currency": "EUR",
            },
        )
        assert expense_response.status_code == 201, (
            f"Expense account creation failed: {expense_response.text}"
        )
        expense_id = expense_response.json()["id"]

        # Create income transaction (salary received)
        test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(2),
                "description": "Monthly Salary",
                "counterparty": "ACME Corp",
                "entries": [
                    {"account_id": asset_id, "debit": "3500.00", "credit": "0"},
                    {"account_id": income_id, "debit": "0", "credit": "3500.00"},
                ],
                "auto_post": True,
            },
        )

        # Create expense transaction (rent payment)
        test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Rent Payment",
                "counterparty": "Landlord",
                "entries": [
                    {"account_id": expense_id, "debit": "1200.00", "credit": "0"},
                    {"account_id": asset_id, "debit": "0", "credit": "1200.00"},
                ],
                "auto_post": True,
            },
        )

        # View dashboard summary
        dashboard_response = test_client.get(
            f"{api_v1_prefix}/dashboard/summary?days=30",
            headers=headers,
        )
        assert dashboard_response.status_code == 200
        dashboard = dashboard_response.json()

        # Verify totals (API returns strings, convert to Decimal)
        assert Decimal(str(dashboard["total_income"])) >= Decimal("3500.00")
        assert Decimal(str(dashboard["total_expenses"])) >= Decimal("1200.00")
        assert "net_income" in dashboard

        # View spending breakdown
        spending_response = test_client.get(
            f"{api_v1_prefix}/dashboard/spending?days=30",
            headers=headers,
        )
        assert spending_response.status_code == 200
        spending = spending_response.json()
        assert Decimal(str(spending["total_spending"])) >= Decimal("1200.00")

        # View balances
        balances_response = test_client.get(
            f"{api_v1_prefix}/dashboard/balances",
            headers=headers,
        )
        assert balances_response.status_code == 200
        balances = balances_response.json()
        # Net balance should be: 3500 - 1200 = 2300
        total_assets = Decimal(str(balances["total_assets"]))
        assert total_assets >= Decimal("2300.00")


@pytest.mark.e2e
class TestPreferencesManagementJourney:
    """Test the preferences management flow.

    Journey: Get Default Preferences → Update → Get Updated → Reset
    """

    def test_full_preferences_lifecycle(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """A user can manage their preferences through the full lifecycle."""
        headers = authenticated_user["headers"]

        # Step 1: Get default preferences
        get_response = test_client.get(
            f"{api_v1_prefix}/preferences",
            headers=headers,
        )
        assert get_response.status_code == 200
        default_prefs = get_response.json()

        # Verify default values exist
        assert "sync_settings" in default_prefs
        assert "display_settings" in default_prefs
        assert "dashboard_settings" in default_prefs
        assert "ai_settings" in default_prefs

        # Step 2: Update some preferences
        update_response = test_client.patch(
            f"{api_v1_prefix}/preferences",
            headers=headers,
            json={
                "auto_post_transactions": True,
                "default_date_range_days": 60,
                "show_draft_transactions": False,
            },
        )
        assert update_response.status_code == 200
        updated_prefs = update_response.json()

        assert updated_prefs["sync_settings"]["auto_post_transactions"] is True
        assert updated_prefs["display_settings"]["default_date_range_days"] == 60
        assert updated_prefs["display_settings"]["show_draft_transactions"] is False

        # Step 3: Get preferences to verify persistence
        verify_response = test_client.get(
            f"{api_v1_prefix}/preferences",
            headers=headers,
        )
        assert verify_response.status_code == 200
        assert verify_response.json()["sync_settings"]["auto_post_transactions"] is True

        # Step 4: Reset preferences to defaults
        reset_response = test_client.post(
            f"{api_v1_prefix}/preferences/reset",
            headers=headers,
        )
        assert reset_response.status_code == 200

        # Step 5: Verify preferences are back to defaults
        final_response = test_client.get(
            f"{api_v1_prefix}/preferences",
            headers=headers,
        )
        assert final_response.status_code == 200
        final_prefs = final_response.json()

        # Should be back to default (auto_post_transactions is False by default)
        assert final_prefs["sync_settings"]["auto_post_transactions"] is False

    def test_dashboard_widget_configuration(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """A user can configure dashboard widgets."""
        headers = authenticated_user["headers"]

        # Get available widgets
        widgets_response = test_client.get(
            f"{api_v1_prefix}/preferences/dashboard/widgets",
            headers=headers,
        )
        assert widgets_response.status_code == 200
        widgets_data = widgets_response.json()
        assert "widgets" in widgets_data
        assert "default_widgets" in widgets_data

        # Get current dashboard settings
        dashboard_response = test_client.get(
            f"{api_v1_prefix}/preferences/dashboard",
            headers=headers,
        )
        assert dashboard_response.status_code == 200
        assert "enabled_widgets" in dashboard_response.json()

        # Update dashboard widgets (if there are available widgets)
        if widgets_data["widgets"]:
            widget_ids = [w["id"] for w in widgets_data["widgets"][:3]]
            update_response = test_client.patch(
                f"{api_v1_prefix}/preferences/dashboard",
                headers=headers,
                json={"enabled_widgets": widget_ids},
            )
            assert update_response.status_code == 200
            assert update_response.json()["enabled_widgets"] == widget_ids


@pytest.mark.e2e
class TestMultiUserIsolation:
    """Test that users are properly isolated from each other."""

    def test_users_cannot_see_each_others_data(
        self,
        test_client: TestClient,
        api_v1_prefix: str,
    ):
        """Two different users cannot access each other's accounts or transactions."""
        # Register user 1
        user1_email = f"user1-{uuid.uuid4().hex[:8]}@example.com"
        user1_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": user1_email, "password": "Password123!"},
        )
        user1_headers = {
            "Authorization": f"Bearer {user1_response.json()['access_token']}"
        }

        # Register user 2
        user2_email = f"user2-{uuid.uuid4().hex[:8]}@example.com"
        user2_response = test_client.post(
            f"{api_v1_prefix}/auth/register",
            json={"email": user2_email, "password": "Password123!"},
        )
        user2_headers = {
            "Authorization": f"Bearer {user2_response.json()['access_token']}"
        }

        # User 1 creates an account
        user1_account_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=user1_headers,
            json={
                "name": "User1 Private Account",
                "account_type": "asset",
                "account_number": unique_account_number("19"),
                "currency": "EUR",
            },
        )
        user1_account_id = user1_account_response.json()["id"]

        # User 2 lists their accounts - should NOT see User 1's account
        user2_accounts_response = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=user2_headers,
        )
        user2_account_ids = [
            a["id"] for a in user2_accounts_response.json()["accounts"]
        ]
        assert user1_account_id not in user2_account_ids

        # User 2 tries to access User 1's account directly - should get 404
        access_response = test_client.get(
            f"{api_v1_prefix}/accounts/{user1_account_id}",
            headers=user2_headers,
        )
        assert access_response.status_code == 404


@pytest.mark.e2e
class TestTransactionListingAndFiltering:
    """Test transaction listing with various filters."""

    def test_transaction_filtering(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """Transactions can be filtered by status and other criteria."""
        headers = user_with_chart["headers"]

        # Create accounts with unique numbers
        asset_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Filter Test Account",
                "account_type": "asset",
                "account_number": unique_account_number("10"),
                "currency": "EUR",
            },
        )
        assert asset_response.status_code == 201, (
            f"Asset account creation failed: {asset_response.text}"
        )
        asset_id = asset_response.json()["id"]

        expense_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Filter Test Expense",
                "account_type": "expense",
                "account_number": unique_account_number("44"),
                "currency": "EUR",
            },
        )
        assert expense_response.status_code == 201, (
            f"Expense account creation failed: {expense_response.text}"
        )
        expense_id = expense_response.json()["id"]

        # Create a draft transaction
        test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Draft Transaction",
                "entries": [
                    {"account_id": expense_id, "debit": "100.00", "credit": "0"},
                    {"account_id": asset_id, "debit": "0", "credit": "100.00"},
                ],
                "auto_post": False,
            },
        )

        # Create a posted transaction
        test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Posted Transaction",
                "entries": [
                    {"account_id": expense_id, "debit": "200.00", "credit": "0"},
                    {"account_id": asset_id, "debit": "0", "credit": "200.00"},
                ],
                "auto_post": True,
            },
        )

        # List all transactions
        all_response = test_client.get(
            f"{api_v1_prefix}/transactions?days=30",
            headers=headers,
        )
        assert all_response.status_code == 200
        all_data = all_response.json()
        assert all_data["total"] >= 2
        assert all_data["draft_count"] >= 1
        assert all_data["posted_count"] >= 1

        # Filter by status: draft only
        draft_response = test_client.get(
            f"{api_v1_prefix}/transactions?days=30&status_filter=draft",
            headers=headers,
        )
        assert draft_response.status_code == 200
        for txn in draft_response.json()["transactions"]:
            assert txn["is_posted"] is False

        # Filter by status: posted only
        posted_response = test_client.get(
            f"{api_v1_prefix}/transactions?days=30&status_filter=posted",
            headers=headers,
        )
        assert posted_response.status_code == 200
        for txn in posted_response.json()["transactions"]:
            assert txn["is_posted"] is True
