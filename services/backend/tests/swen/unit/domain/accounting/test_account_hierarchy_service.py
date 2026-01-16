"""Tests for AccountHierarchyService."""

from uuid import uuid4

import pytest

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.services import AccountHierarchyService
from swen.domain.shared.exceptions import ValidationError


class MockAccountRepository:
    """Mock repository for testing hierarchy service."""

    def __init__(self):
        self.accounts = {}

    async def save(self, account: Account) -> None:
        """Save account."""
        self.accounts[account.id] = account

    async def find_by_id(self, account_id):
        """Find account by ID."""
        return self.accounts.get(account_id)

    async def is_parent(self, account_id) -> bool:
        """Check if account has children."""
        return any(acc.parent_id == account_id for acc in self.accounts.values())

    async def find_descendants(self, parent_id):
        """Find all descendants recursively."""
        descendants = []
        to_process = [parent_id]
        seen = set()

        while to_process:
            current_id = to_process.pop()
            if current_id in seen:
                continue
            seen.add(current_id)

            children = [
                acc for acc in self.accounts.values() if acc.parent_id == current_id
            ]
            descendants.extend(children)
            to_process.extend([c.id for c in children])

        return descendants


@pytest.fixture
def mock_repo():
    """Create mock repository."""
    return MockAccountRepository()


@pytest.fixture
def hierarchy_service(mock_repo):
    """Create hierarchy service with mock repo."""
    return AccountHierarchyService(mock_repo)


@pytest.fixture
def test_user_id():
    """Test user ID."""
    return uuid4()


class TestAccountHierarchyService:
    """Tests for AccountHierarchyService."""

    @pytest.mark.asyncio
    async def test_validate_hierarchy_simple_parent_child(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test valid simple parent-child relationship."""
        # Arrange
        parent = Account("Food", AccountType.EXPENSE, "4000", test_user_id)
        child = Account("Groceries", AccountType.EXPENSE, "4010", test_user_id)

        await mock_repo.save(parent)
        await mock_repo.save(child)

        child.set_parent(parent)

        # Act & Assert - should not raise
        await hierarchy_service.validate_hierarchy(child, parent)

    @pytest.mark.asyncio
    async def test_validate_hierarchy_prevents_circular_reference_direct(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test that direct circular reference is prevented (A -> A)."""
        # Arrange
        account = Account("Self Reference", AccountType.EXPENSE, "4000", test_user_id)
        await mock_repo.save(account)

        # Act & Assert
        # Note: Account.set_parent already prevents this, but test service too
        with pytest.raises(ValidationError, match="circular reference"):
            # Simulate what would happen if we bypassed entity validation
            account._parent_id = account.id
            await hierarchy_service.validate_hierarchy(account, account)

    @pytest.mark.asyncio
    async def test_validate_hierarchy_prevents_circular_reference_indirect(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test that indirect circular reference is prevented (A -> B -> A)."""
        # Arrange
        account_a = Account("Account A", AccountType.EXPENSE, "4000", test_user_id)
        account_b = Account("Account B", AccountType.EXPENSE, "4010", test_user_id)

        await mock_repo.save(account_a)
        await mock_repo.save(account_b)

        # Create chain: A -> B
        account_a.set_parent(account_b)

        # Act & Assert - Try to create B -> A (would create cycle)
        with pytest.raises(ValidationError, match="circular reference"):
            await hierarchy_service.validate_hierarchy(account_b, account_a)

    @pytest.mark.asyncio
    async def test_validate_hierarchy_prevents_circular_reference_three_levels(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test that circular reference is prevented (A -> B -> C -> A)."""
        # Arrange
        account_a = Account("Account A", AccountType.EXPENSE, "4000", test_user_id)
        account_b = Account("Account B", AccountType.EXPENSE, "4010", test_user_id)
        account_c = Account("Account C", AccountType.EXPENSE, "4020", test_user_id)

        await mock_repo.save(account_a)
        await mock_repo.save(account_b)
        await mock_repo.save(account_c)

        # Create chain: A -> B -> C
        account_a.set_parent(account_b)
        account_b.set_parent(account_c)

        # Act & Assert - Try to create C -> A (would create cycle)
        with pytest.raises(ValidationError, match="circular reference"):
            await hierarchy_service.validate_hierarchy(account_c, account_a)

    @pytest.mark.asyncio
    async def test_validate_hierarchy_enforces_max_depth(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test that maximum depth of 3 levels is enforced."""
        # Arrange - Create 3-level hierarchy
        level_0 = Account("Root", AccountType.EXPENSE, "4000", test_user_id)
        level_1 = Account("Level 1", AccountType.EXPENSE, "4010", test_user_id)
        level_2 = Account("Level 2", AccountType.EXPENSE, "4020", test_user_id)
        level_3 = Account("Level 3", AccountType.EXPENSE, "4030", test_user_id)

        await mock_repo.save(level_0)
        await mock_repo.save(level_1)
        await mock_repo.save(level_2)
        await mock_repo.save(level_3)

        # Create hierarchy: Root <- L1 <- L2
        level_1.set_parent(level_0)
        level_2.set_parent(level_1)

        # Act & Assert - Try to add L3 as child of L2 (would be 4th level)
        with pytest.raises(ValidationError, match="Maximum hierarchy depth"):
            await hierarchy_service.validate_hierarchy(level_3, level_2)

    @pytest.mark.asyncio
    async def test_validate_hierarchy_allows_max_depth_exactly(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test that exactly 3 levels is allowed."""
        # Arrange
        level_0 = Account("Root", AccountType.EXPENSE, "4000", test_user_id)
        level_1 = Account("Level 1", AccountType.EXPENSE, "4010", test_user_id)
        level_2 = Account("Level 2", AccountType.EXPENSE, "4020", test_user_id)

        await mock_repo.save(level_0)
        await mock_repo.save(level_1)
        await mock_repo.save(level_2)

        # Create hierarchy: Root <- L1
        level_1.set_parent(level_0)

        # Act & Assert - Add L2 as child of L1 (3 levels total) - should work
        level_2.set_parent(level_1)
        await hierarchy_service.validate_hierarchy(level_2, level_1)

    @pytest.mark.asyncio
    async def test_can_delete_returns_true_for_leaf_account(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test can_delete returns True for account without children."""
        # Arrange
        account = Account("Leaf Account", AccountType.EXPENSE, "4000", test_user_id)
        await mock_repo.save(account)

        # Act
        result = await hierarchy_service.can_delete(account)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_can_delete_returns_false_for_parent_account(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test can_delete returns False for account with children."""
        # Arrange
        parent = Account("Parent", AccountType.EXPENSE, "4000", test_user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", test_user_id)

        await mock_repo.save(parent)
        await mock_repo.save(child)

        child.set_parent(parent)

        # Act
        result = await hierarchy_service.can_delete(parent)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_is_parent_returns_true_when_has_children(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test is_parent returns True when account has children."""
        # Arrange
        parent = Account("Parent", AccountType.EXPENSE, "4000", test_user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", test_user_id)

        await mock_repo.save(parent)
        await mock_repo.save(child)

        child.set_parent(parent)

        # Act
        result = await hierarchy_service.is_parent(parent.id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_is_parent_returns_false_when_no_children(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test is_parent returns False when account has no children."""
        # Arrange
        account = Account("Leaf", AccountType.EXPENSE, "4000", test_user_id)
        await mock_repo.save(account)

        # Act
        result = await hierarchy_service.is_parent(account.id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_descendants_single_level(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test getting all descendants for single level."""
        # Arrange
        parent = Account("Parent", AccountType.EXPENSE, "4000", test_user_id)
        child1 = Account("Child 1", AccountType.EXPENSE, "4010", test_user_id)
        child2 = Account("Child 2", AccountType.EXPENSE, "4020", test_user_id)

        await mock_repo.save(parent)
        await mock_repo.save(child1)
        await mock_repo.save(child2)

        child1.set_parent(parent)
        child2.set_parent(parent)

        # Act
        descendants = await hierarchy_service.get_all_descendants(parent.id)

        # Assert
        assert len(descendants) == 2
        assert child1 in descendants
        assert child2 in descendants

    @pytest.mark.asyncio
    async def test_get_all_descendants_multiple_levels(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test getting all descendants recursively."""
        # Arrange - Create tree: Root -> A -> A1, A2 and Root -> B
        root = Account("Root", AccountType.EXPENSE, "4000", test_user_id)
        child_a = Account("Child A", AccountType.EXPENSE, "4010", test_user_id)
        child_b = Account("Child B", AccountType.EXPENSE, "4020", test_user_id)
        grandchild_a1 = Account(
            "Grandchild A1",
            AccountType.EXPENSE,
            "4011",
            test_user_id,
        )
        grandchild_a2 = Account(
            "Grandchild A2",
            AccountType.EXPENSE,
            "4012",
            test_user_id,
        )

        await mock_repo.save(root)
        await mock_repo.save(child_a)
        await mock_repo.save(child_b)
        await mock_repo.save(grandchild_a1)
        await mock_repo.save(grandchild_a2)

        child_a.set_parent(root)
        child_b.set_parent(root)
        grandchild_a1.set_parent(child_a)
        grandchild_a2.set_parent(child_a)

        # Act
        descendants = await hierarchy_service.get_all_descendants(root.id)

        # Assert
        assert len(descendants) == 4
        assert child_a in descendants
        assert child_b in descendants
        assert grandchild_a1 in descendants
        assert grandchild_a2 in descendants

    @pytest.mark.asyncio
    async def test_get_all_descendants_empty_for_leaf(
        self,
        hierarchy_service,
        mock_repo,
        test_user_id,
    ):
        """Test getting descendants for leaf account returns empty list."""
        # Arrange
        leaf = Account("Leaf", AccountType.EXPENSE, "4000", test_user_id)
        await mock_repo.save(leaf)

        # Act
        descendants = await hierarchy_service.get_all_descendants(leaf.id)

        # Assert
        assert len(descendants) == 0
