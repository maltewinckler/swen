"""Tests for UpdateAccountCommand and DeactivateAccountCommand with hierarchy."""

from uuid import uuid4

import pytest

from swen.application.commands.accounting import (
    DeactivateAccountCommand,
    UpdateAccountCommand,
)
from swen.application.commands.accounting.update_account_command import ParentAction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import (
    AccountAlreadyExistsError,
    AccountCannotBeDeactivatedError,
    AccountNotFoundError,
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

    async def is_parent(self, account_id) -> bool:
        """Check if account has children."""
        return any(acc.parent_id == account_id for acc in self.accounts.values())


@pytest.fixture
def test_user_id():
    """Test user ID."""
    return uuid4()


@pytest.fixture
def mock_repo():
    """Create mock repository."""
    return MockAccountRepository()


@pytest.fixture
def hierarchy_service(mock_repo):
    """Create hierarchy service."""
    return AccountHierarchyService(mock_repo)


@pytest.fixture
def update_command(mock_repo, hierarchy_service):
    """Create update command."""
    return UpdateAccountCommand(mock_repo, hierarchy_service)


@pytest.fixture
def deactivate_command(mock_repo, hierarchy_service):
    """Create deactivate command."""
    return DeactivateAccountCommand(mock_repo, hierarchy_service)


class TestUpdateAccountCommand:
    """Tests for UpdateAccountCommand."""

    @pytest.mark.asyncio
    async def test_update_account_name(
        self,
        update_command,
        mock_repo,
        test_user_id,
    ):
        """Test updating account name."""
        # Arrange
        account = Account("Old Name", AccountType.EXPENSE, "4000", test_user_id)
        await mock_repo.save(account)

        # Act
        updated = await update_command.execute(
            account_id=account.id,
            name="New Name",
        )

        # Assert
        assert updated.name == "New Name"
        assert updated.id == account.id

    @pytest.mark.asyncio
    async def test_update_account_description(
        self,
        update_command,
        mock_repo,
        test_user_id,
    ):
        """Test updating account description."""
        # Arrange
        account = Account("Test", AccountType.EXPENSE, "4000", test_user_id)
        await mock_repo.save(account)

        # Act
        updated = await update_command.execute(
            account_id=account.id,
            description="New description",
        )

        # Assert
        assert updated.description == "New description"

    @pytest.mark.asyncio
    async def test_update_set_parent(self, update_command, mock_repo, test_user_id):
        """Test setting parent on an account."""
        # Arrange
        parent = Account("Parent", AccountType.EXPENSE, "4000", test_user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", test_user_id)
        await mock_repo.save(parent)
        await mock_repo.save(child)

        # Act
        updated = await update_command.execute(
            account_id=child.id,
            parent_id=parent.id,
            parent_action=ParentAction.SET,
        )

        # Assert
        assert updated.parent_id == parent.id

    @pytest.mark.asyncio
    async def test_update_change_parent(self, update_command, mock_repo, test_user_id):
        """Test changing parent to different parent."""
        # Arrange
        old_parent = Account("Old Parent", AccountType.EXPENSE, "4000", test_user_id)
        new_parent = Account("New Parent", AccountType.EXPENSE, "4100", test_user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", test_user_id)

        await mock_repo.save(old_parent)
        await mock_repo.save(new_parent)
        await mock_repo.save(child)

        child.set_parent(old_parent)
        await mock_repo.save(child)

        # Act
        updated = await update_command.execute(
            account_id=child.id,
            parent_id=new_parent.id,
            parent_action=ParentAction.SET,
        )

        # Assert
        assert updated.parent_id == new_parent.id

    @pytest.mark.asyncio
    async def test_update_remove_parent(self, update_command, mock_repo, test_user_id):
        """Test removing parent from sub-account."""
        # Arrange
        parent = Account("Parent", AccountType.EXPENSE, "4000", test_user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", test_user_id)
        await mock_repo.save(parent)
        await mock_repo.save(child)

        child.set_parent(parent)
        await mock_repo.save(child)

        assert child.parent_id == parent.id

        # Act - Use ParentAction.REMOVE to remove parent
        updated = await update_command.execute(
            account_id=child.id,
            parent_action=ParentAction.REMOVE,
        )

        # Assert
        assert updated.parent_id is None

    @pytest.mark.asyncio
    async def test_update_parent_validates_hierarchy(
        self,
        update_command,
        mock_repo,
        test_user_id,
    ):
        """Test that hierarchy validation is enforced."""
        # Arrange - Create 3-level hierarchy at max depth
        level_0 = Account("Root", AccountType.EXPENSE, "4000", test_user_id)
        level_1 = Account("Level 1", AccountType.EXPENSE, "4010", test_user_id)
        level_2 = Account("Level 2", AccountType.EXPENSE, "4020", test_user_id)
        level_3 = Account("Level 3", AccountType.EXPENSE, "4030", test_user_id)

        await mock_repo.save(level_0)
        await mock_repo.save(level_1)
        await mock_repo.save(level_2)
        await mock_repo.save(level_3)

        level_1.set_parent(level_0)
        level_2.set_parent(level_1)

        # Act & Assert - Try to set level_3 as child of level_2 (would exceed depth)
        with pytest.raises(ValidationError, match="Maximum hierarchy depth"):
            await update_command.execute(
                account_id=level_3.id,
                parent_id=level_2.id,
                parent_action=ParentAction.SET,
            )

    @pytest.mark.asyncio
    async def test_update_parent_prevents_circular_reference(
        self,
        update_command,
        mock_repo,
        test_user_id,
    ):
        """Test that update prevents circular references."""
        # Arrange - A is parent of B
        account_a = Account("Account A", AccountType.EXPENSE, "4000", test_user_id)
        account_b = Account("Account B", AccountType.EXPENSE, "4010", test_user_id)

        await mock_repo.save(account_a)
        await mock_repo.save(account_b)

        account_b.set_parent(account_a)
        await mock_repo.save(account_b)

        # Act & Assert - Try to make A child of B (would create cycle)
        with pytest.raises(ValidationError, match="circular reference"):
            await update_command.execute(
                account_id=account_a.id,
                parent_id=account_b.id,
                parent_action=ParentAction.SET,
            )

    @pytest.mark.asyncio
    async def test_update_duplicate_name_raises_error(
        self,
        update_command,
        mock_repo,
        test_user_id,
    ):
        """Test that duplicate names are rejected."""
        # Arrange
        account1 = Account("Account 1", AccountType.EXPENSE, "4000", test_user_id)
        account2 = Account("Account 2", AccountType.EXPENSE, "4010", test_user_id)
        await mock_repo.save(account1)
        await mock_repo.save(account2)

        # Act & Assert
        with pytest.raises(AccountAlreadyExistsError):
            await update_command.execute(
                account_id=account2.id,
                name="Account 1",  # Duplicate
            )

    @pytest.mark.asyncio
    async def test_update_account_not_found_raises_error(self, update_command):
        """Test that updating non-existent account raises error."""
        # Act & Assert
        non_existent_id = uuid4()
        with pytest.raises(AccountNotFoundError):
            await update_command.execute(
                account_id=non_existent_id,
                name="New Name",
            )

    @pytest.mark.asyncio
    async def test_update_parent_not_found_raises_error(
        self,
        update_command,
        mock_repo,
        test_user_id,
    ):
        """Test that setting non-existent parent raises error."""
        # Arrange
        account = Account("Test", AccountType.EXPENSE, "4000", test_user_id)
        await mock_repo.save(account)

        # Act & Assert
        non_existent_parent_id = uuid4()
        with pytest.raises(AccountNotFoundError):
            await update_command.execute(
                account_id=account.id,
                parent_id=non_existent_parent_id,
                parent_action=ParentAction.SET,
            )


class TestDeactivateAccountCommand:
    """Tests for DeactivateAccountCommand."""

    @pytest.mark.asyncio
    async def test_deactivate_leaf_account(
        self,
        deactivate_command,
        mock_repo,
        test_user_id,
    ):
        """Test deactivating account without children."""
        # Arrange
        account = Account("Test", AccountType.EXPENSE, "4000", test_user_id)
        await mock_repo.save(account)

        # Act
        deactivated = await deactivate_command.execute(account_id=account.id)

        # Assert
        assert deactivated.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_prevents_deactivating_parent(
        self,
        deactivate_command,
        mock_repo,
        test_user_id,
    ):
        """Test that accounts with children cannot be deactivated."""
        # Arrange
        parent = Account("Parent", AccountType.EXPENSE, "4000", test_user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", test_user_id)
        await mock_repo.save(parent)
        await mock_repo.save(child)

        child.set_parent(parent)
        await mock_repo.save(child)

        # Act & Assert
        with pytest.raises(AccountCannotBeDeactivatedError):
            await deactivate_command.execute(account_id=parent.id)

    @pytest.mark.asyncio
    async def test_deactivate_allows_after_children_removed(
        self,
        deactivate_command,
        mock_repo,
        test_user_id,
    ):
        """Test that parent can be deactivated after children are removed."""
        # Arrange
        parent = Account("Parent", AccountType.EXPENSE, "4000", test_user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", test_user_id)
        await mock_repo.save(parent)
        await mock_repo.save(child)

        child.set_parent(parent)
        await mock_repo.save(child)

        # Remove parent from child
        child.remove_parent()
        await mock_repo.save(child)

        # Act
        deactivated = await deactivate_command.execute(account_id=parent.id)

        # Assert
        assert deactivated.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_child_account_allowed(
        self,
        deactivate_command,
        mock_repo,
        test_user_id,
    ):
        """Test that child accounts can be deactivated."""
        # Arrange
        parent = Account("Parent", AccountType.EXPENSE, "4000", test_user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", test_user_id)
        await mock_repo.save(parent)
        await mock_repo.save(child)

        child.set_parent(parent)
        await mock_repo.save(child)

        # Act
        deactivated = await deactivate_command.execute(account_id=child.id)

        # Assert
        assert deactivated.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_account_not_found_raises_error(self, deactivate_command):
        """Test that deactivating non-existent account raises error."""
        # Act & Assert
        non_existent_id = uuid4()
        with pytest.raises(AccountNotFoundError):
            await deactivate_command.execute(account_id=non_existent_id)
