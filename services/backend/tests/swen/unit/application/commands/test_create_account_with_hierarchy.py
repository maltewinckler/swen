"""Tests for CreateAccountCommand with hierarchy functionality."""

from uuid import uuid4

import pytest

from swen.application.commands.accounting import (
    CreateAccountCommand,
    ParentAction,
    UpdateAccountCommand,
)
from swen.application.ports.identity import CurrentUser
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    InvalidAccountTypeError,
    InvalidCurrencyError,
)
from swen.domain.accounting.services import AccountHierarchyService
from swen.domain.shared.exceptions import ValidationError


class MockAccountRepository:
    """Mock repository for testing."""

    def __init__(self):
        self.accounts = {}

    async def save(self, account: Account) -> None:
        """Save account."""
        self.accounts[account.id] = account

    async def find_by_id(self, account_id):
        """Find by ID."""
        return self.accounts.get(account_id)

    async def find_by_name(self, name: str):
        """Find by name."""
        for acc in self.accounts.values():
            if acc.name == name:
                return acc
        return None

    async def find_by_account_number(self, account_number: str):
        """Find by account number."""
        for acc in self.accounts.values():
            if acc.account_number == account_number:
                return acc
        return None

    async def is_parent(self, account_id) -> bool:
        """Check if account has children."""
        return any(acc.parent_id == account_id for acc in self.accounts.values())


@pytest.fixture
def current_user():
    """Create user context."""
    return CurrentUser(user_id=uuid4(), email="test@example.com")


@pytest.fixture
def mock_repo():
    """Create mock repository."""
    return MockAccountRepository()


@pytest.fixture
def hierarchy_service(mock_repo):
    """Create hierarchy service."""
    return AccountHierarchyService(mock_repo)


@pytest.fixture
def create_command(mock_repo, hierarchy_service, current_user):
    """Create command instance."""
    return CreateAccountCommand(mock_repo, hierarchy_service, current_user)


@pytest.fixture
def update_command(mock_repo, hierarchy_service, current_user):
    """Create update command instance."""
    return UpdateAccountCommand(mock_repo, hierarchy_service, current_user)


class TestCreateAccountCommand:
    """Tests for CreateAccountCommand."""

    @pytest.mark.asyncio
    async def test_create_simple_account(self, create_command):
        """Test creating account without parent."""
        # Act
        account = await create_command.execute(
            name="Groceries",
            account_type="expense",
            account_number="4010",
            description="Food purchases",
        )

        # Assert
        assert account.name == "Groceries"
        assert account.account_type == AccountType.EXPENSE
        assert account.account_number == "4010"
        assert account.parent_id is None
        assert account.description == "Food purchases"

    @pytest.mark.asyncio
    async def test_create_sub_account(self, create_command):
        """Test creating sub-account with parent."""
        # Arrange - Create parent first
        parent = await create_command.execute(
            name="Food & Drink",
            account_type="expense",
            account_number="4000",
        )

        # Act - Create child
        child = await create_command.execute(
            name="Groceries",
            account_type="expense",
            account_number="4010",
            parent_id=parent.id,
        )

        # Assert
        assert child.parent_id == parent.id
        assert child.account_type == parent.account_type

    @pytest.mark.asyncio
    async def test_create_sub_account_validates_parent_exists(self, create_command):
        """Test that parent must exist."""
        # Act & Assert
        non_existent_id = uuid4()
        with pytest.raises(AccountNotFoundError):
            await create_command.execute(
                name="Child",
                account_type="expense",
                account_number="4010",
                parent_id=non_existent_id,
            )

    @pytest.mark.asyncio
    async def test_create_sub_account_validates_same_type(
        self,
        create_command,
        mock_repo,
    ):
        """Test that child must have same type as parent."""
        # Arrange - Create expense parent
        parent = await create_command.execute(
            name="Expenses",
            account_type="expense",
            account_number="4000",
        )

        # Act & Assert - Try to create asset child
        with pytest.raises(ValidationError, match="same account type"):
            # We need to bypass command validation to test entity validation
            child = Account(
                "Asset Child",
                AccountType.ASSET,
                "1000",
                create_command._user_id,
            )
            await mock_repo.save(child)
            child.set_parent(parent)

    @pytest.mark.asyncio
    async def test_create_prevents_circular_reference(
        self,
        create_command,
        hierarchy_service,
        mock_repo,
    ):
        """Test that circular references are prevented."""
        # Arrange - Create two accounts
        account_a = await create_command.execute(
            name="Account A",
            account_type="expense",
            account_number="4000",
        )
        account_b = await create_command.execute(
            name="Account B",
            account_type="expense",
            account_number="4010",
        )

        # Make A child of B
        account_a._parent_id = account_b.id
        await mock_repo.save(account_a)

        # Act & Assert - Try to make B child of A (would create cycle)
        with pytest.raises(ValidationError, match="circular reference"):
            await hierarchy_service.validate_hierarchy(account_b, account_a)

    @pytest.mark.asyncio
    async def test_create_enforces_max_depth(self, create_command, hierarchy_service):
        """Test that maximum depth is enforced."""
        # Arrange - Create 3-level hierarchy
        level_0 = await create_command.execute(
            name="Root",
            account_type="expense",
            account_number="4000",
        )
        level_1 = await create_command.execute(
            name="Level 1",
            account_type="expense",
            account_number="4010",
            parent_id=level_0.id,
        )
        level_2 = await create_command.execute(
            name="Level 2",
            account_type="expense",
            account_number="4020",
            parent_id=level_1.id,
        )

        # Act & Assert - Try to create level 3 (would exceed max depth)
        with pytest.raises(ValidationError, match="Maximum hierarchy depth"):
            await create_command.execute(
                name="Level 3",
                account_type="expense",
                account_number="4030",
                parent_id=level_2.id,
            )

    @pytest.mark.asyncio
    async def test_create_allows_exactly_three_levels(self, create_command):
        """Test that exactly 3 levels is allowed."""
        # Arrange & Act - Create 3-level hierarchy
        level_0 = await create_command.execute(
            name="Root",
            account_type="expense",
            account_number="4000",
        )
        level_1 = await create_command.execute(
            name="Level 1",
            account_type="expense",
            account_number="4010",
            parent_id=level_0.id,
        )
        level_2 = await create_command.execute(
            name="Level 2",
            account_type="expense",
            account_number="4020",
            parent_id=level_1.id,
        )

        # Assert - All should be created successfully
        assert level_2.parent_id == level_1.id
        assert level_1.parent_id == level_0.id
        assert level_0.parent_id is None

    @pytest.mark.asyncio
    async def test_create_duplicate_account_number_raises_error(self, create_command):
        """Test that duplicate account numbers are rejected."""
        # Arrange - Create first account
        await create_command.execute(
            name="First",
            account_type="expense",
            account_number="4000",
        )

        # Act & Assert - Try to create duplicate
        with pytest.raises(AccountAlreadyExistsError):
            await create_command.execute(
                name="Second",
                account_type="expense",
                account_number="4000",  # Duplicate
            )

    @pytest.mark.asyncio
    async def test_create_duplicate_name_raises_error(self, create_command):
        """Test that duplicate names are rejected."""
        # Arrange
        await create_command.execute(
            name="Groceries",
            account_type="expense",
            account_number="4000",
        )

        # Act & Assert
        with pytest.raises(AccountAlreadyExistsError):
            await create_command.execute(
                name="Groceries",  # Duplicate
                account_type="expense",
                account_number="4010",
            )

    @pytest.mark.asyncio
    async def test_create_invalid_account_type_raises_error(self, create_command):
        """Test that invalid account type raises error."""
        # Act & Assert
        with pytest.raises(InvalidAccountTypeError):
            await create_command.execute(
                name="Test",
                account_type="invalid_type",
                account_number="4000",
            )

    @pytest.mark.asyncio
    async def test_create_invalid_currency_raises_error(self, create_command):
        """Test that invalid currency raises InvalidCurrencyError with details."""
        # Act & Assert
        with pytest.raises(InvalidCurrencyError) as exc_info:
            await create_command.execute(
                name="Test",
                account_type="expense",
                account_number="4000",
                currency="INVALID",
            )

        # Verify error details
        error = exc_info.value
        assert "INVALID" in str(error)
        assert error.details["currency"] == "INVALID"
        assert "valid_currencies" in error.details


class TestUpdateAccountParentAction:
    """Tests for UpdateAccountCommand parent_action functionality."""

    @pytest.mark.asyncio
    async def test_parent_action_keep_preserves_parent(
        self,
        create_command,
        update_command,
    ):
        """Test that parent_action=KEEP doesn't change the parent."""
        # Arrange - Create parent and child
        parent = await create_command.execute(
            name="Parent",
            account_type="expense",
            account_number="4000",
        )
        child = await create_command.execute(
            name="Child",
            account_type="expense",
            account_number="4010",
            parent_id=parent.id,
        )
        assert child.parent_id == parent.id

        # Act - Update name only with KEEP (default)
        updated = await update_command.execute(
            account_id=child.id,
            name="Renamed Child",
            parent_action=ParentAction.KEEP,
        )

        # Assert - Parent should be unchanged
        assert updated.name == "Renamed Child"
        assert updated.parent_id == parent.id

    @pytest.mark.asyncio
    async def test_parent_action_keep_is_default(
        self,
        create_command,
        update_command,
    ):
        """Test that parent_action defaults to KEEP."""
        # Arrange - Create parent and child
        parent = await create_command.execute(
            name="Parent",
            account_type="expense",
            account_number="4000",
        )
        child = await create_command.execute(
            name="Child",
            account_type="expense",
            account_number="4010",
            parent_id=parent.id,
        )

        # Act - Update without specifying parent_action
        updated = await update_command.execute(
            account_id=child.id,
            name="Renamed Child",
            # parent_action not specified - should default to KEEP
        )

        # Assert - Parent should be unchanged
        assert updated.parent_id == parent.id

    @pytest.mark.asyncio
    async def test_parent_action_set_changes_parent(
        self,
        create_command,
        update_command,
    ):
        """Test that parent_action=SET changes the parent."""
        # Arrange - Create accounts
        old_parent = await create_command.execute(
            name="Old Parent",
            account_type="expense",
            account_number="4000",
        )
        new_parent = await create_command.execute(
            name="New Parent",
            account_type="expense",
            account_number="4001",
        )
        child = await create_command.execute(
            name="Child",
            account_type="expense",
            account_number="4010",
            parent_id=old_parent.id,
        )
        assert child.parent_id == old_parent.id

        # Act - Change parent with SET
        updated = await update_command.execute(
            account_id=child.id,
            parent_id=new_parent.id,
            parent_action=ParentAction.SET,
        )

        # Assert - Parent should be changed
        assert updated.parent_id == new_parent.id

    @pytest.mark.asyncio
    async def test_parent_action_set_requires_parent_id(
        self,
        create_command,
        update_command,
    ):
        """Test that parent_action=SET requires parent_id."""
        # Arrange
        account = await create_command.execute(
            name="Account",
            account_type="expense",
            account_number="4000",
        )

        # Act & Assert - SET without parent_id should raise
        with pytest.raises(ValueError, match="parent_id is required"):
            await update_command.execute(
                account_id=account.id,
                parent_action=ParentAction.SET,
                # parent_id not provided
            )

    @pytest.mark.asyncio
    async def test_parent_action_remove_detaches_from_parent(
        self,
        create_command,
        update_command,
    ):
        """Test that parent_action=REMOVE makes account top-level."""
        # Arrange - Create parent and child
        parent = await create_command.execute(
            name="Parent",
            account_type="expense",
            account_number="4000",
        )
        child = await create_command.execute(
            name="Child",
            account_type="expense",
            account_number="4010",
            parent_id=parent.id,
        )
        assert child.parent_id == parent.id

        # Act - Remove parent
        updated = await update_command.execute(
            account_id=child.id,
            parent_action=ParentAction.REMOVE,
        )

        # Assert - Should be top-level now
        assert updated.parent_id is None

    @pytest.mark.asyncio
    async def test_parent_action_remove_on_top_level_is_noop(
        self,
        create_command,
        update_command,
    ):
        """Test that REMOVE on already top-level account is safe."""
        # Arrange - Create top-level account
        account = await create_command.execute(
            name="Top Level",
            account_type="expense",
            account_number="4000",
        )
        assert account.parent_id is None

        # Act - Remove parent (already None)
        updated = await update_command.execute(
            account_id=account.id,
            parent_action=ParentAction.REMOVE,
        )

        # Assert - Still top-level, no error
        assert updated.parent_id is None

    @pytest.mark.asyncio
    async def test_parent_action_set_validates_hierarchy(
        self,
        create_command,
        update_command,
    ):
        """Test that SET validates hierarchy constraints."""
        # Arrange - Create child and would-be parent
        child = await create_command.execute(
            name="Child",
            account_type="expense",
            account_number="4000",
        )
        # Create asset account (different type)
        asset_account = await create_command.execute(
            name="Asset",
            account_type="asset",
            account_number="1000",
        )

        # Act & Assert - Can't set parent of different type
        with pytest.raises(Exception):  # ValidationError from domain
            await update_command.execute(
                account_id=child.id,
                parent_id=asset_account.id,
                parent_action=ParentAction.SET,
            )


class TestUpdateAccountNumber:
    """Tests for UpdateAccountCommand account_number functionality."""

    @pytest.mark.asyncio
    async def test_update_account_number(
        self,
        create_command,
        update_command,
    ):
        """Test successfully changing an account number."""
        # Arrange
        account = await create_command.execute(
            name="Groceries",
            account_type="expense",
            account_number="4000",
        )
        assert account.account_number == "4000"

        # Act
        updated = await update_command.execute(
            account_id=account.id,
            account_number="4100",
        )

        # Assert
        assert updated.account_number == "4100"
        assert updated.name == "Groceries"  # Name unchanged

    @pytest.mark.asyncio
    async def test_update_account_number_duplicate_raises_error(
        self,
        create_command,
        update_command,
    ):
        """Test that changing to an existing account number raises error."""
        # Arrange - Create two accounts
        account1 = await create_command.execute(
            name="Account 1",
            account_type="expense",
            account_number="4000",
        )
        account2 = await create_command.execute(
            name="Account 2",
            account_type="expense",
            account_number="4100",
        )

        # Act & Assert - Try to change account2's number to account1's
        with pytest.raises(AccountAlreadyExistsError):
            await update_command.execute(
                account_id=account2.id,
                account_number="4000",  # Duplicate
            )

    @pytest.mark.asyncio
    async def test_update_account_number_same_value_is_allowed(
        self,
        create_command,
        update_command,
    ):
        """Test that updating with same account number doesn't raise error."""
        # Arrange
        account = await create_command.execute(
            name="Test",
            account_type="expense",
            account_number="4000",
        )

        # Act - Update with same number (no-op)
        updated = await update_command.execute(
            account_id=account.id,
            account_number="4000",  # Same as current
        )

        # Assert - Should succeed
        assert updated.account_number == "4000"

    @pytest.mark.asyncio
    async def test_update_account_number_empty_raises_error(
        self,
        create_command,
        update_command,
    ):
        """Test that empty account number raises ValidationError."""
        # Arrange
        account = await create_command.execute(
            name="Test",
            account_type="expense",
            account_number="4000",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="cannot be empty"):
            await update_command.execute(
                account_id=account.id,
                account_number="",
            )

    @pytest.mark.asyncio
    async def test_update_account_number_whitespace_only_raises_error(
        self,
        create_command,
        update_command,
    ):
        """Test that whitespace-only account number raises ValidationError."""
        # Arrange
        account = await create_command.execute(
            name="Test",
            account_type="expense",
            account_number="4000",
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="cannot be empty"):
            await update_command.execute(
                account_id=account.id,
                account_number="   ",
            )

    @pytest.mark.asyncio
    async def test_update_account_number_and_name_together(
        self,
        create_command,
        update_command,
    ):
        """Test updating account number and name in a single call."""
        # Arrange
        account = await create_command.execute(
            name="Old Name",
            account_type="expense",
            account_number="4000",
        )

        # Act
        updated = await update_command.execute(
            account_id=account.id,
            name="New Name",
            account_number="4100",
        )

        # Assert
        assert updated.name == "New Name"
        assert updated.account_number == "4100"
