"""Integration tests for AccountRepository hierarchy methods."""

import pytest

from swen.domain.accounting.entities import Account, AccountType
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
)


@pytest.mark.asyncio
class TestAccountRepositoryHierarchy:
    """Test hierarchy-specific repository methods."""

    async def test_find_children_single_level(self, async_session, current_user):
        """Test finding direct children of a parent."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        parent = Account("Parent", AccountType.EXPENSE, "4000", user_id)
        child1 = Account("Child 1", AccountType.EXPENSE, "4010", user_id)
        child2 = Account("Child 2", AccountType.EXPENSE, "4020", user_id)
        unrelated = Account("Unrelated", AccountType.EXPENSE, "4030", user_id)

        await repo.save(parent)

        # Set parent BEFORE saving children
        child1.set_parent(parent)
        child2.set_parent(parent)

        await repo.save(child1)
        await repo.save(child2)
        await repo.save(unrelated)

        # Ensure all changes are flushed to the DB before querying
        await async_session.flush()

        # Act
        children = await repo.find_children(parent.id)

        # Assert
        assert len(children) == 2
        child_ids = {c.id for c in children}
        assert child1.id in child_ids
        assert child2.id in child_ids
        assert unrelated.id not in child_ids

    async def test_find_children_empty_for_leaf(self, async_session, current_user):
        """Test that leaf accounts have no children."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        leaf = Account("Leaf", AccountType.EXPENSE, "4000", user_id)
        await repo.save(leaf)

        # Act
        children = await repo.find_children(leaf.id)

        # Assert
        assert len(children) == 0

    async def test_find_descendants_multiple_levels(self, async_session, current_user):
        """Test finding all descendants recursively."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        # Create tree: Root -> A -> A1, A2; Root -> B
        root = Account("Root", AccountType.EXPENSE, "4000", user_id)
        child_a = Account("Child A", AccountType.EXPENSE, "4010", user_id)
        child_b = Account("Child B", AccountType.EXPENSE, "4020", user_id)
        grandchild_a1 = Account(
            "Grandchild A1", AccountType.EXPENSE, "4011", user_id,
        )
        grandchild_a2 = Account(
            "Grandchild A2", AccountType.EXPENSE, "4012", user_id,
        )

        await repo.save(root)
        await repo.save(child_a)
        await repo.save(child_b)
        await repo.save(grandchild_a1)
        await repo.save(grandchild_a2)

        child_a.set_parent(root)
        child_b.set_parent(root)
        grandchild_a1.set_parent(child_a)
        grandchild_a2.set_parent(child_a)

        await repo.save(child_a)
        await repo.save(child_b)
        await repo.save(grandchild_a1)
        await repo.save(grandchild_a2)

        # Act
        descendants = await repo.find_descendants(root.id)

        # Assert
        assert len(descendants) == 4
        descendant_ids = {d.id for d in descendants}
        assert child_a.id in descendant_ids
        assert child_b.id in descendant_ids
        assert grandchild_a1.id in descendant_ids
        assert grandchild_a2.id in descendant_ids

    async def test_find_descendants_from_middle_level(
        self,
        async_session,
        current_user,
    ):
        """Test finding descendants starting from middle of tree."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        root = Account("Root", AccountType.EXPENSE, "4000", user_id)
        middle = Account("Middle", AccountType.EXPENSE, "4010", user_id)
        leaf1 = Account("Leaf 1", AccountType.EXPENSE, "4011", user_id)
        leaf2 = Account("Leaf 2", AccountType.EXPENSE, "4012", user_id)

        await repo.save(root)
        await repo.save(middle)
        await repo.save(leaf1)
        await repo.save(leaf2)

        middle.set_parent(root)
        leaf1.set_parent(middle)
        leaf2.set_parent(middle)

        await repo.save(middle)
        await repo.save(leaf1)
        await repo.save(leaf2)

        # Act - Get descendants of middle, not root
        descendants = await repo.find_descendants(middle.id)

        # Assert - Should only get leaf nodes, not root
        assert len(descendants) == 2
        descendant_ids = {d.id for d in descendants}
        assert leaf1.id in descendant_ids
        assert leaf2.id in descendant_ids
        assert root.id not in descendant_ids

    async def test_is_parent_true_when_has_children(self, async_session, current_user):
        """Test is_parent returns True for accounts with children."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        parent = Account("Parent", AccountType.EXPENSE, "4000", user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", user_id)

        await repo.save(parent)
        await repo.save(child)

        child.set_parent(parent)
        await repo.save(child)

        # Act
        result = await repo.is_parent(parent.id)

        # Assert
        assert result is True

    async def test_is_parent_false_when_no_children(
        self,
        async_session,
        current_user,
    ):
        """Test is_parent returns False for leaf accounts."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        leaf = Account("Leaf", AccountType.EXPENSE, "4000", user_id)
        await repo.save(leaf)

        # Act
        result = await repo.is_parent(leaf.id)

        # Assert
        assert result is False

    async def test_get_hierarchy_path_single_account(
        self,
        async_session,
        current_user,
    ):
        """Test getting path for root account."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        root = Account("Root", AccountType.EXPENSE, "4000", user_id)
        await repo.save(root)

        # Act
        path = await repo.get_hierarchy_path(root.id)

        # Assert
        assert len(path) == 1
        assert path[0].id == root.id

    async def test_get_hierarchy_path_multiple_levels(
        self,
        async_session,
        current_user,
    ):
        """Test getting complete path from root to leaf."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        # Create: Root -> Middle -> Leaf
        root = Account("Root", AccountType.EXPENSE, "4000", user_id)
        middle = Account("Middle", AccountType.EXPENSE, "4010", user_id)
        leaf = Account("Leaf", AccountType.EXPENSE, "4020", user_id)

        await repo.save(root)
        await repo.save(middle)
        await repo.save(leaf)

        middle.set_parent(root)
        leaf.set_parent(middle)

        await repo.save(middle)
        await repo.save(leaf)

        # Act
        path = await repo.get_hierarchy_path(leaf.id)

        # Assert
        assert len(path) == 3
        assert path[0].id == root.id
        assert path[1].id == middle.id
        assert path[2].id == leaf.id

    async def test_find_by_parent_id_alias(self, async_session, current_user):
        """Test find_by_parent_id is alias for find_children."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        parent = Account("Parent", AccountType.EXPENSE, "4000", user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", user_id)

        await repo.save(parent)
        await repo.save(child)

        child.set_parent(parent)
        await repo.save(child)

        # Act
        children_direct = await repo.find_children(parent.id)
        children_alias = await repo.find_by_parent_id(parent.id)

        # Assert
        assert len(children_direct) == len(children_alias) == 1
        assert children_direct[0].id == children_alias[0].id == child.id

    async def test_hierarchy_persists_across_saves(
        self,
        async_session,
        current_user,
    ):
        """Test that parent_id is correctly persisted and retrieved."""
        # Arrange
        repo = AccountRepositorySQLAlchemy(async_session, current_user)
        user_id = current_user.user_id

        parent = Account("Parent", AccountType.EXPENSE, "4000", user_id)
        child = Account("Child", AccountType.EXPENSE, "4010", user_id)

        await repo.save(parent)
        await repo.save(child)

        child.set_parent(parent)
        await repo.save(child)

        # Clear to force fresh read from DB
        await async_session.commit()

        # Act - Retrieve from database
        retrieved_child = await repo.find_by_id(child.id)

        # Assert
        assert retrieved_child is not None
        assert retrieved_child.parent_id == parent.id
