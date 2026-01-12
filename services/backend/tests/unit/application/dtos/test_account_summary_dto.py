"""Tests for AccountSummaryDTO parent_id functionality."""

from uuid import uuid4

import pytest

from swen.application.dtos.accounting import AccountSummaryDTO
from swen.domain.accounting.entities import Account, AccountType


class TestAccountSummaryDTO:
    """Test AccountSummaryDTO creation and parent_id handling."""

    def test_from_entity_without_parent(self):
        """Test DTO creation for account without parent."""
        # Arrange
        user_id = uuid4()
        account = Account("Expenses", AccountType.EXPENSE, "4000", user_id)

        # Act
        dto = AccountSummaryDTO.from_entity(account)

        # Assert
        assert dto.name == "Expenses"
        assert dto.parent_id is None

    def test_from_entity_with_parent(self):
        """Test DTO creation for sub-account with parent."""
        # Arrange
        user_id = uuid4()
        parent = Account("Food & Drink", AccountType.EXPENSE, "4000", user_id)
        child = Account("Groceries", AccountType.EXPENSE, "4010", user_id)
        child.set_parent(parent)

        # Act
        dto = AccountSummaryDTO.from_entity(child)

        # Assert
        assert dto.name == "Groceries"
        assert dto.parent_id == str(parent.id)

    def test_to_dict_includes_parent_id(self):
        """Test to_dict includes parent_id field."""
        # Arrange
        user_id = uuid4()
        parent = Account("Food", AccountType.EXPENSE, "4000", user_id)
        child = Account("Bars", AccountType.EXPENSE, "4010", user_id)
        child.set_parent(parent)

        # Act
        dto = AccountSummaryDTO.from_entity(child)
        result = dto.to_dict()

        # Assert
        assert "parent_id" in result
        assert result["parent_id"] == str(parent.id)

    def test_to_dict_parent_id_null_for_root(self):
        """Test to_dict has null parent_id for root accounts."""
        # Arrange
        user_id = uuid4()
        root = Account("Expenses", AccountType.EXPENSE, "4000", user_id)

        # Act
        dto = AccountSummaryDTO.from_entity(root)
        result = dto.to_dict()

        # Assert
        assert "parent_id" in result
        assert result["parent_id"] is None
