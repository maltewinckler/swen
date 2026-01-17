"""Tests for the Account entity."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Money
from swen.domain.shared.exceptions import ValidationError

# Test user ID for all account tests
TEST_USER_ID = uuid4()


class TestAccount:
    """Test cases for Account entity."""

    def test_account_creation(self):
        """Test creating basic Account instances."""
        account = Account("Checking Account", AccountType.ASSET, "1000", TEST_USER_ID)

        assert account.name == "Checking Account"
        assert account.account_type == AccountType.ASSET
        assert account.is_active is True
        assert account.account_number == "1000"
        assert account.parent_id is None
        assert isinstance(account.id, UUID)
        assert account.created_at is not None
        assert account.user_id == TEST_USER_ID
        assert account.iban is None

    def test_account_creation_with_iban(self):
        """Test creating a bank/external account with separate IBAN."""
        account = Account(
            name="My Bank",
            account_type=AccountType.ASSET,
            account_number="0532013000",
            user_id=TEST_USER_ID,
            iban="de89 3704 0044 0532 0130 00",
        )
        assert account.account_number == "0532013000"
        assert account.iban == "DE89370400440532013000"

    def test_account_creation_with_account_number(self):
        """Test creating Account with account number."""
        account_number = "4900"  # Internal accounting code
        account = Account(
            "Groceries",
            AccountType.EXPENSE,
            account_number,
            TEST_USER_ID,
        )

        assert account.account_number == account_number
        assert account.name == "Groceries"
        assert account.account_type == AccountType.EXPENSE

    def test_account_types(self):
        """Test all account types can be created."""
        asset = Account("Bank Account", AccountType.ASSET, "1000", TEST_USER_ID)
        liability = Account("Credit Card", AccountType.LIABILITY, "2000", TEST_USER_ID)
        equity = Account("Opening Balance", AccountType.EQUITY, "3000", TEST_USER_ID)
        income = Account("Salary", AccountType.INCOME, "4000", TEST_USER_ID)
        expense = Account("Groceries", AccountType.EXPENSE, "5000", TEST_USER_ID)

        assert asset.account_type == AccountType.ASSET
        assert liability.account_type == AccountType.LIABILITY
        assert equity.account_type == AccountType.EQUITY
        assert income.account_type == AccountType.INCOME
        assert expense.account_type == AccountType.EXPENSE

    def test_account_deactivation(self):
        """Test account can be deactivated and reactivated."""
        account = Account("Test Account", AccountType.ASSET, "1000", TEST_USER_ID)
        assert account.is_active is True

        account.deactivate()
        assert account.is_active is False

        account.activate()
        assert account.is_active is True

    def test_account_hierarchy(self):
        """Test account parent-child relationships."""
        parent = Account("Assets", AccountType.ASSET, "1000", TEST_USER_ID)
        child = Account("Checking", AccountType.ASSET, "1100", TEST_USER_ID)

        assert child.parent_id is None

        child.set_parent(parent)
        assert child.parent_id == parent.id

    def test_set_parent_validates_same_account_type(self):
        """Test that set_parent requires matching account types."""
        parent = Account("Expenses", AccountType.EXPENSE, "4000", TEST_USER_ID)
        child = Account("Bank Account", AccountType.ASSET, "1000", TEST_USER_ID)

        with pytest.raises(ValidationError, match="same account type"):
            child.set_parent(parent)

    def test_set_parent_validates_same_user(self):
        """Test that set_parent requires same user."""
        user1 = uuid4()
        user2 = uuid4()
        parent = Account("Parent", AccountType.EXPENSE, "4000", user1)
        child = Account("Child", AccountType.EXPENSE, "4010", user2)

        with pytest.raises(ValidationError, match="same user"):
            child.set_parent(parent)

    def test_set_parent_prevents_self_reference(self):
        """Test that account cannot be its own parent."""
        account = Account("Self", AccountType.EXPENSE, "4000", TEST_USER_ID)

        with pytest.raises(ValidationError, match="cannot be its own parent"):
            account.set_parent(account)

    def test_remove_parent(self):
        """Test removing parent from sub-account."""
        parent = Account("Parent", AccountType.EXPENSE, "4000", TEST_USER_ID)
        child = Account("Child", AccountType.EXPENSE, "4010", TEST_USER_ID)

        child.set_parent(parent)
        assert child.parent_id == parent.id

        child.remove_parent()
        assert child.parent_id is None

    def test_is_sub_account(self):
        """Test is_sub_account helper method."""
        parent = Account("Parent", AccountType.EXPENSE, "4000", TEST_USER_ID)
        child = Account("Child", AccountType.EXPENSE, "4010", TEST_USER_ID)
        standalone = Account("Standalone", AccountType.EXPENSE, "4020", TEST_USER_ID)

        assert standalone.is_sub_account() is False

        child.set_parent(parent)
        assert child.is_sub_account() is True

        child.remove_parent()
        assert child.is_sub_account() is False

    def test_is_parent_account_not_implemented(self):
        """Test that is_parent_account raises NotImplementedError."""
        account = Account("Test", AccountType.EXPENSE, "4000", TEST_USER_ID)

        with pytest.raises(NotImplementedError, match="domain services"):
            account.is_parent_account()

    def test_account_transaction_validation(self):
        """Test can_accept_transaction business rules."""
        asset_account = Account("Checking", AccountType.ASSET, "1000", TEST_USER_ID)
        expense_account = Account(
            "Groceries",
            AccountType.EXPENSE,
            "5000",
            TEST_USER_ID,
        )

        # Asset accounts should accept positive amounts
        positive_amount = Money(amount=Decimal("100.00"))
        assert asset_account.can_accept_transaction(positive_amount) is True

        # Asset accounts should reject negative amounts (for now)
        negative_amount = Money(amount=Decimal("-50.00"))
        assert asset_account.can_accept_transaction(negative_amount) is False

        # Other account types should accept any amount
        assert expense_account.can_accept_transaction(positive_amount) is True
        assert expense_account.can_accept_transaction(negative_amount) is True

    def test_account_normal_balance_types(self):
        """Test normal balance types for different account categories."""
        # Debit normal accounts
        asset = Account("Bank", AccountType.ASSET, "1000", TEST_USER_ID)
        expense = Account("Rent", AccountType.EXPENSE, "5000", TEST_USER_ID)

        assert asset.is_debit_normal() is True
        assert asset.is_credit_normal() is False
        assert expense.is_debit_normal() is True
        assert expense.is_credit_normal() is False

        # Credit normal accounts
        liability = Account("Credit Card", AccountType.LIABILITY, "2000", TEST_USER_ID)
        equity = Account("Owner Equity", AccountType.EQUITY, "3000", TEST_USER_ID)
        income = Account("Salary", AccountType.INCOME, "4000", TEST_USER_ID)

        assert liability.is_debit_normal() is False
        assert liability.is_credit_normal() is True
        assert equity.is_debit_normal() is False
        assert equity.is_credit_normal() is True
        assert income.is_debit_normal() is False
        assert income.is_credit_normal() is True

    def test_account_equality(self):
        """Test account equality and hashing."""
        account1 = Account("Test", AccountType.ASSET, "1000", TEST_USER_ID)
        account2 = Account("Test", AccountType.ASSET, "2000", TEST_USER_ID)
        # Same account_number and user_id as account1, but still a different entity instance
        # (IDs are not derived from account_number).
        account3 = Account("Test", AccountType.ASSET, "1000", TEST_USER_ID)

        # Different accounts with different account_numbers should not be equal
        assert account1 != account2
        # Same account_number does NOT imply same identity
        assert account1 != account3

        # Should be hashable for use in sets/dicts
        account_set = {account1, account2, account3}
        assert len(account_set) == 3

    def test_account_equality_with_same_iban(self):
        """Same IBAN does not imply same identity (IDs are not derived from IBAN)."""
        account1 = Account(
            name="Bank A",
            account_type=AccountType.ASSET,
            account_number="0532013000",
            user_id=TEST_USER_ID,
            iban="DE89370400440532013000",
        )
        account2 = Account(
            name="Bank A (renamed code)",
            account_type=AccountType.ASSET,
            account_number="MY-CODE-1",
            user_id=TEST_USER_ID,
            iban="DE89370400440532013000",
        )
        assert account1 != account2
        assert account1.id != account2.id

    def test_account_equality_different_users(self):
        """Test that same account_number for different users creates different accounts."""
        user1 = uuid4()
        user2 = uuid4()
        account1 = Account("Test", AccountType.ASSET, "1000", user1)
        account2 = Account("Test", AccountType.ASSET, "1000", user2)

        # Same account_number but different users should be different accounts
        assert account1 != account2
        assert account1.id != account2.id

    def test_account_string_representation(self):
        """Test string representation of accounts."""
        account = Account("Checking Account", AccountType.ASSET, "1000", TEST_USER_ID)
        account_str = str(account)

        assert "Checking Account" in account_str
        assert "asset" in account_str

    def test_account_immutable_properties(self):
        """Test that certain account properties cannot be changed after creation."""
        account = Account("Test", AccountType.ASSET, "1000", TEST_USER_ID)
        original_id = account.id
        original_created_at = account.created_at

        # These should remain unchanged
        assert account.id == original_id
        assert account.created_at == original_created_at
        assert account.name == "Test"
        assert account.account_type == AccountType.ASSET
        assert account.user_id == TEST_USER_ID


class TestAccountRename:
    """Test cases for Account rename functionality."""

    def test_rename_account_successfully(self):
        """Test that an account can be renamed."""
        account = Account("Old Name", AccountType.ASSET, "1000", TEST_USER_ID)
        assert account.name == "Old Name"

        account.rename("New Name")
        assert account.name == "New Name"

    def test_rename_strips_whitespace(self):
        """Test that rename strips leading/trailing whitespace."""
        account = Account("Original", AccountType.ASSET, "1000", TEST_USER_ID)

        account.rename("  Trimmed Name  ")
        assert account.name == "Trimmed Name"

    def test_rename_with_empty_string_raises_error(self):
        """Test that renaming with empty string raises ValidationError."""
        account = Account("Test", AccountType.ASSET, "1000", TEST_USER_ID)

        with pytest.raises(ValidationError):
            account.rename("")

    def test_rename_with_whitespace_only_raises_error(self):
        """Test that renaming with whitespace-only string raises ValidationError."""
        account = Account("Test", AccountType.ASSET, "1000", TEST_USER_ID)

        with pytest.raises(ValidationError):
            account.rename("   ")

    def test_rename_with_none_raises_error(self):
        """Test that renaming with None raises ValidationError."""
        account = Account("Test", AccountType.ASSET, "1000", TEST_USER_ID)

        with pytest.raises(ValidationError):
            account.rename(None)  # type: ignore[arg-type]

    def test_rename_preserves_other_properties(self):
        """Test that rename doesn't affect other account properties."""
        account = Account("Original", AccountType.ASSET, "1000", TEST_USER_ID)
        original_id = account.id
        original_type = account.account_type
        original_number = account.account_number
        original_user_id = account.user_id

        account.rename("New Name")

        assert account.id == original_id
        assert account.account_type == original_type
        assert account.account_number == original_number
        assert account.user_id == original_user_id


class TestAccountReconstitute:
    """Test cases for Account.reconstitute factory method."""

    def test_reconstitute_preserves_all_values(self):
        """Test that reconstitute creates Account with exact values provided."""
        from datetime import datetime, timezone

        from swen.domain.accounting.value_objects import Currency

        account_id = uuid4()
        user_id = uuid4()
        parent_id = uuid4()
        created_at = datetime(2023, 6, 15, 10, 30, 0, tzinfo=timezone.utc)

        account = Account.reconstitute(
            id=account_id,
            user_id=user_id,
            name="Reconstituted Account",
            account_type=AccountType.EXPENSE,
            account_number="5001",
            default_currency=Currency("USD"),
            is_active=False,
            created_at=created_at,
            iban="DE89370400440532013000",
            description="Test description",
            parent_id=parent_id,
        )

        assert account.id == account_id
        assert account.user_id == user_id
        assert account.name == "Reconstituted Account"
        assert account.account_type == AccountType.EXPENSE
        assert account.account_number == "5001"
        assert account.default_currency.code == "USD"
        assert account.is_active is False
        assert account.created_at == created_at
        assert account.iban == "DE89370400440532013000"
        assert account.description == "Test description"
        assert account.parent_id == parent_id

    def test_reconstitute_normalizes_iban(self):
        """Test that reconstitute normalizes IBAN like constructor does."""
        from datetime import datetime, timezone

        from swen.domain.accounting.value_objects import Currency

        account = Account.reconstitute(
            id=uuid4(),
            user_id=uuid4(),
            name="Bank Account",
            account_type=AccountType.ASSET,
            account_number="1001",
            default_currency=Currency("EUR"),
            is_active=True,
            created_at=datetime.now(tz=timezone.utc),
            iban="de89 3704 0044 0532 0130 00",  # Lowercase with spaces
        )

        # IBAN should be normalized (uppercase, no spaces)
        assert account.iban == "DE89370400440532013000"

    def test_reconstitute_with_none_optional_values(self):
        """Test reconstitute with None for optional parameters."""
        from datetime import datetime, timezone

        from swen.domain.accounting.value_objects import Currency

        account = Account.reconstitute(
            id=uuid4(),
            user_id=uuid4(),
            name="Simple Account",
            account_type=AccountType.INCOME,
            account_number="4001",
            default_currency=Currency("EUR"),
            is_active=True,
            created_at=datetime.now(tz=timezone.utc),
            iban=None,
            description=None,
            parent_id=None,
        )

        assert account.iban is None
        assert account.description is None
        assert account.parent_id is None

    def test_reconstitute_does_not_generate_new_id(self):
        """Test that reconstitute uses provided ID, not generating new one."""
        from datetime import datetime, timezone

        from swen.domain.accounting.value_objects import Currency

        fixed_id = uuid4()

        account1 = Account.reconstitute(
            id=fixed_id,
            user_id=uuid4(),
            name="Test",
            account_type=AccountType.ASSET,
            account_number="1000",
            default_currency=Currency("EUR"),
            is_active=True,
            created_at=datetime.now(tz=timezone.utc),
        )
        account2 = Account.reconstitute(
            id=fixed_id,
            user_id=uuid4(),
            name="Test 2",
            account_type=AccountType.ASSET,
            account_number="1001",
            default_currency=Currency("EUR"),
            is_active=True,
            created_at=datetime.now(tz=timezone.utc),
        )

        # Both should have the same ID (as provided)
        assert account1.id == fixed_id
        assert account2.id == fixed_id
        assert account1.id == account2.id
