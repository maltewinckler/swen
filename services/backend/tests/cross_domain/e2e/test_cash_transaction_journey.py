"""
E2E tests for cash transaction user journeys.

Tests for users who primarily use cash without bank connections:
1. Initialize essential accounts (manual onboarding)
2. Quick cash expense entry
3. Manual transaction with full details
4. View transactions in dashboard
5. Categorize and recategorize transactions

This represents the "offline" or "cash-only" user journey.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def recent_date(days_ago: int = 0) -> str:
    """Get an ISO date string for N days ago (within dashboard window)."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def unique_account_number(prefix: str = "") -> str:
    """Generate a unique account number."""
    return f"{prefix}{uuid4().hex[:6]}"


@pytest.mark.e2e
class TestCashTransactionJourney:
    """Test the complete cash transaction flow without bank connection."""

    def test_cash_user_full_journey(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """
        Complete journey for a cash-only user:
        1. Initialize essential accounts
        2. Add cash expense
        3. View in transactions
        4. See reflected in dashboard
        """
        headers = authenticated_user["headers"]

        # Step 1: Initialize essential accounts (manual onboarding path)
        essentials_response = test_client.post(
            f"{api_v1_prefix}/accounts/init-essentials",
            headers=headers,
        )
        assert essentials_response.status_code in (200, 201), (
            f"Init essentials failed: {essentials_response.text}"
        )
        essentials_data = essentials_response.json()
        assert essentials_data["accounts_created"] == 3

        # Step 2: Verify essential accounts exist
        accounts_response = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=headers,
        )
        accounts = accounts_response.json()["accounts"]
        account_numbers = {a["account_number"]: a for a in accounts}

        assert "1000" in account_numbers, "Bargeld (Cash) account missing"
        assert "4900" in account_numbers, "Sonstiges (Other) expense account missing"
        assert "3100" in account_numbers, "Sonstige Einnahmen (Other Income) missing"

        cash_account_id = account_numbers["1000"]["id"]
        expense_account_id = account_numbers["4900"]["id"]

        # Step 3: Create a simple cash expense
        # This simulates the /quick route CashExpenseModal
        simple_response = test_client.post(
            f"{api_v1_prefix}/transactions/simple",
            headers=headers,
            json={
                "description": "Coffee at bakery",
                "amount": "-4.50",  # Negative for expense
                "date": recent_date(0),
                "asset_account": "1000",  # Bargeld
                "category_account": "4900",  # Sonstiges
                "auto_post": True,
            },
        )
        assert simple_response.status_code == 201, (
            f"Simple transaction failed: {simple_response.text}"
        )
        simple_txn = simple_response.json()
        assert simple_txn["description"] == "Coffee at bakery"
        assert simple_txn["is_posted"] is True

        # Step 4: Create full transaction with all details
        full_response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Weekly groceries",
                "counterparty": "Local Market",
                "entries": [
                    {
                        "account_id": expense_account_id,
                        "debit": "85.00",
                        "credit": "0",
                    },
                    {
                        "account_id": cash_account_id,
                        "debit": "0",
                        "credit": "85.00",
                    },
                ],
                "auto_post": True,
            },
        )
        assert full_response.status_code == 201, (
            f"Full transaction failed: {full_response.text}"
        )

        # Step 5: List transactions - should see both
        txn_list = test_client.get(
            f"{api_v1_prefix}/transactions?days=30",
            headers=headers,
        )
        assert txn_list.status_code == 200
        txn_data = txn_list.json()
        assert txn_data["total"] >= 2
        assert txn_data["posted_count"] >= 2

        # Step 6: View dashboard - should reflect expenses
        dashboard = test_client.get(
            f"{api_v1_prefix}/dashboard/summary",
            headers=headers,
        )
        assert dashboard.status_code == 200
        dashboard_data = dashboard.json()

        # Total expenses should include our transactions
        total_expenses = Decimal(str(dashboard_data["total_expenses"]))
        assert total_expenses >= Decimal("89.50"), (
            f"Expected >= 89.50, got {total_expenses}"
        )

    def test_split_cash_expense(
        self,
        test_client: TestClient,
        authenticated_user: dict,
        api_v1_prefix: str,
    ):
        """Create a split expense from cash (multiple categories)."""
        headers = authenticated_user["headers"]

        # Initialize accounts first
        test_client.post(
            f"{api_v1_prefix}/accounts/init-chart",
            headers=headers,
            json={"template": "minimal"},
        )

        # Get accounts
        accounts = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=headers,
        ).json()["accounts"]

        asset_account = next(a for a in accounts if a["account_type"] == "asset")
        expense_accounts = [a for a in accounts if a["account_type"] == "expense"]

        # Ensure we have at least 2 expense accounts
        if len(expense_accounts) < 2:
            new_expense = test_client.post(
                f"{api_v1_prefix}/accounts",
                headers=headers,
                json={
                    "name": "Entertainment",
                    "account_type": "expense",
                    "account_number": unique_account_number("45"),
                    "currency": "EUR",
                },
            )
            expense_accounts.append(new_expense.json())

        # Create split transaction
        split_response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(0),
                "description": "Mixed shopping",
                "entries": [
                    {
                        "account_id": expense_accounts[0]["id"],
                        "debit": "30.00",
                        "credit": "0",
                    },
                    {
                        "account_id": expense_accounts[1]["id"],
                        "debit": "20.00",
                        "credit": "0",
                    },
                    {
                        "account_id": asset_account["id"],
                        "debit": "0",
                        "credit": "50.00",
                    },
                ],
                "auto_post": True,
            },
        )
        assert split_response.status_code == 201
        txn = split_response.json()

        # Should have 3 entries
        assert len(txn["entries"]) == 3


@pytest.mark.e2e
class TestManualTransactionEditing:
    """Test editing and recategorizing transactions."""

    def test_recategorize_transaction(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """User can change the category of an existing transaction."""
        headers = user_with_chart["headers"]

        # Get accounts
        accounts = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=headers,
        ).json()["accounts"]

        asset = next(a for a in accounts if a["account_type"] == "asset")
        expense1 = next(a for a in accounts if a["account_type"] == "expense")

        # Create second expense account
        expense2_response = test_client.post(
            f"{api_v1_prefix}/accounts",
            headers=headers,
            json={
                "name": "Correct Category",
                "account_type": "expense",
                "account_number": unique_account_number("46"),
                "currency": "EUR",
            },
        )
        expense2 = expense2_response.json()

        # Create transaction with wrong category
        create_response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Miscategorized expense",
                "entries": [
                    {"account_id": expense1["id"], "debit": "100.00", "credit": "0"},
                    {"account_id": asset["id"], "debit": "0", "credit": "100.00"},
                ],
                "auto_post": True,
            },
        )
        txn_id = create_response.json()["id"]

        # Recategorize using category_account_id shortcut
        update_response = test_client.put(
            f"{api_v1_prefix}/transactions/{txn_id}",
            headers=headers,
            json={
                "category_account_id": expense2["id"],
            },
        )
        assert update_response.status_code == 200

        # Verify entries updated
        get_response = test_client.get(
            f"{api_v1_prefix}/transactions/{txn_id}",
            headers=headers,
        )
        updated_txn = get_response.json()

        # Should now have expense2 instead of expense1
        debit_entries = [
            e
            for e in updated_txn["entries"]
            if e["debit"] is not None and Decimal(e["debit"]) > 0
        ]
        assert len(debit_entries) == 1
        assert debit_entries[0]["account_id"] == expense2["id"]

    def test_edit_transaction_description(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """User can update transaction description and counterparty."""
        headers = user_with_chart["headers"]

        # Get accounts
        accounts = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=headers,
        ).json()["accounts"]

        asset = next(a for a in accounts if a["account_type"] == "asset")
        expense = next(a for a in accounts if a["account_type"] == "expense")

        # Create transaction
        create_response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Original description",
                "counterparty": "Original Store",
                "entries": [
                    {"account_id": expense["id"], "debit": "50.00", "credit": "0"},
                    {"account_id": asset["id"], "debit": "0", "credit": "50.00"},
                ],
                "auto_post": True,
            },
        )
        txn_id = create_response.json()["id"]

        # Update description and counterparty
        update_response = test_client.put(
            f"{api_v1_prefix}/transactions/{txn_id}",
            headers=headers,
            json={
                "description": "Updated description",
                "counterparty": "New Store Name",
            },
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["description"] == "Updated description"
        assert updated["counterparty"] == "New Store Name"


@pytest.mark.e2e
class TestDraftTransactionFlow:
    """Test draft transaction workflow."""

    def test_create_draft_then_post(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """Create as draft, review, then post."""
        headers = user_with_chart["headers"]

        # Get accounts
        accounts = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=headers,
        ).json()["accounts"]

        asset = next(a for a in accounts if a["account_type"] == "asset")
        expense = next(a for a in accounts if a["account_type"] == "expense")

        # Create as draft
        create_response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "Draft for review",
                "entries": [
                    {"account_id": expense["id"], "debit": "75.00", "credit": "0"},
                    {"account_id": asset["id"], "debit": "0", "credit": "75.00"},
                ],
                "auto_post": False,  # Keep as draft
            },
        )
        assert create_response.status_code == 201
        txn = create_response.json()
        assert txn["is_posted"] is False
        txn_id = txn["id"]

        # Verify appears in drafts
        drafts = test_client.get(
            f"{api_v1_prefix}/transactions?days=30&status_filter=draft",
            headers=headers,
        )
        draft_ids = [t["id"] for t in drafts.json()["transactions"]]
        assert txn_id in draft_ids

        # Post the transaction
        post_response = test_client.post(
            f"{api_v1_prefix}/transactions/{txn_id}/post",
            headers=headers,
        )
        assert post_response.status_code == 200
        assert post_response.json()["is_posted"] is True

        # Should now appear in posted
        posted = test_client.get(
            f"{api_v1_prefix}/transactions?days=30&status_filter=posted",
            headers=headers,
        )
        posted_ids = [t["id"] for t in posted.json()["transactions"]]
        assert txn_id in posted_ids

    def test_unpost_then_delete_draft(
        self,
        test_client: TestClient,
        user_with_chart: dict,
        api_v1_prefix: str,
    ):
        """Unpost a transaction, then delete it."""
        headers = user_with_chart["headers"]

        # Get accounts
        accounts = test_client.get(
            f"{api_v1_prefix}/accounts",
            headers=headers,
        ).json()["accounts"]

        asset = next(a for a in accounts if a["account_type"] == "asset")
        expense = next(a for a in accounts if a["account_type"] == "expense")

        # Create and post
        create_response = test_client.post(
            f"{api_v1_prefix}/transactions",
            headers=headers,
            json={
                "date": recent_date(1),
                "description": "To be unposted",
                "entries": [
                    {"account_id": expense["id"], "debit": "25.00", "credit": "0"},
                    {"account_id": asset["id"], "debit": "0", "credit": "25.00"},
                ],
                "auto_post": True,
            },
        )
        txn_id = create_response.json()["id"]

        # Unpost
        unpost_response = test_client.post(
            f"{api_v1_prefix}/transactions/{txn_id}/unpost",
            headers=headers,
        )
        assert unpost_response.status_code == 200
        assert unpost_response.json()["is_posted"] is False

        # Delete (now that it's a draft)
        delete_response = test_client.delete(
            f"{api_v1_prefix}/transactions/{txn_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        # Verify gone
        get_response = test_client.get(
            f"{api_v1_prefix}/transactions/{txn_id}",
            headers=headers,
        )
        assert get_response.status_code == 404
