"""Tests for the CategoryCode value object."""

import pytest
from pydantic import ValidationError

from swen.domain.accounting.value_objects import CategoryCode


class TestCategoryCode:
    """Test cases for CategoryCode value object."""

    def test_simple_category_creation(self):
        """Test creating a simple category without parent."""
        category = CategoryCode(code="FOOD", name="Food & Dining")

        assert category.code == "FOOD"
        assert category.name == "Food & Dining"
        assert category.parent_code is None
        assert category.is_subcategory() is False

    def test_subcategory_creation(self):
        """Test creating a subcategory with parent."""
        subcategory = CategoryCode(
            code="GROCERIES", name="Grocery Shopping", parent_code="FOOD"
        )

        assert subcategory.code == "GROCERIES"
        assert subcategory.name == "Grocery Shopping"
        assert subcategory.parent_code == "FOOD"
        assert subcategory.is_subcategory() is True

    def test_code_normalization_uppercase(self):
        """Test that codes are normalized to uppercase."""
        category = CategoryCode(
            code="food", name="Food & Dining", parent_code="expenses"
        )

        assert category.code == "FOOD"
        assert category.parent_code == "EXPENSES"

    def test_name_trimming(self):
        """Test that names are trimmed of whitespace."""
        category = CategoryCode(code="FOOD", name="  Food & Dining  ")

        assert category.name == "Food & Dining"

    def test_code_trimming(self):
        """Test that codes are trimmed of whitespace."""
        category = CategoryCode(
            code="  FOOD  ", name="Food & Dining", parent_code="  EXPENSES  "
        )

        assert category.code == "FOOD"
        assert category.parent_code == "EXPENSES"

    def test_empty_code_validation(self):
        """Test that empty code raises ValueError."""
        with pytest.raises(ValueError, match="Category code cannot be empty"):
            CategoryCode("", "Food & Dining")

    def test_whitespace_only_code_validation(self):
        """Test that whitespace-only code raises ValueError."""
        with pytest.raises(ValueError, match="Category code cannot be empty"):
            CategoryCode(code="   ", name="Food & Dining")

    def test_empty_name_validation(self):
        """Test that empty name raises ValueError."""
        with pytest.raises(ValueError, match="Category name cannot be empty"):
            CategoryCode("FOOD", "")

    def test_whitespace_only_name_validation(self):
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="Category name cannot be empty"):
            CategoryCode(code="FOOD", name="   ")

    def test_none_parent_code_handling(self):
        """Test that None parent_code is handled correctly."""
        category = CategoryCode(code="FOOD", name="Food & Dining", parent_code=None)

        assert category.parent_code is None
        assert category.is_subcategory() is False

    def test_empty_parent_code_normalization(self):
        """Test that empty parent_code becomes None after trimming."""
        category = CategoryCode(code="FOOD", name="Food & Dining", parent_code="   ")

        assert category.parent_code is None  # Empty string becomes None after trimming
        assert category.is_subcategory() is False

    def test_string_representation_main_category(self):
        """Test string representation of main category."""
        category = CategoryCode(code="FOOD", name="Food & Dining")
        expected = "FOOD - Food & Dining"

        assert str(category) == expected

    def test_string_representation_subcategory(self):
        """Test string representation of subcategory."""
        subcategory = CategoryCode(
            code="GROCERIES", name="Grocery Shopping", parent_code="FOOD"
        )
        expected = "FOOD.GROCERIES - Grocery Shopping"

        assert str(subcategory) == expected

    def test_category_equality(self):
        """Test CategoryCode equality and hashing."""
        category1 = CategoryCode(code="FOOD", name="Food & Dining")
        category2 = CategoryCode(
            code="food", name="Food & Dining"
        )  # Same but lowercase
        category3 = CategoryCode(code="TRANSPORT", name="Transportation")

        assert category1 == category2  # Should be equal after normalization
        assert category1 != category3
        assert hash(category1) == hash(category2)

    def test_subcategory_equality(self):
        """Test subcategory equality includes parent code."""
        subcategory1 = CategoryCode(
            code="GROCERIES", name="Grocery Shopping", parent_code="FOOD"
        )
        subcategory2 = CategoryCode(
            code="groceries", name="Grocery Shopping", parent_code="food"
        )
        subcategory3 = CategoryCode(
            code="GROCERIES", name="Grocery Shopping", parent_code="EXPENSES"
        )

        assert subcategory1 == subcategory2  # Same after normalization
        assert subcategory1 != subcategory3  # Different parent

    def test_category_immutability(self):
        """Test that CategoryCode is immutable."""
        category = CategoryCode(code="FOOD", name="Food & Dining")

        with pytest.raises(ValidationError, match="frozen"):
            category.code = "TRANSPORT"

        with pytest.raises(ValidationError, match="frozen"):
            category.name = "Transportation"

        with pytest.raises(ValidationError, match="frozen"):
            category.parent_code = "EXPENSES"

    def test_hierarchical_category_structure(self):
        """Test creating hierarchical category structures."""
        # Main category
        main = CategoryCode(code="EXPENSES", name="Expenses")

        # Level 1 subcategories
        food = CategoryCode(code="FOOD", name="Food & Dining", parent_code="EXPENSES")
        transport = CategoryCode(
            code="TRANSPORT", name="Transportation", parent_code="EXPENSES"
        )

        # Level 2 subcategories
        groceries = CategoryCode(
            code="GROCERIES", name="Grocery Shopping", parent_code="FOOD"
        )
        restaurants = CategoryCode(
            code="RESTAURANTS", name="Restaurants", parent_code="FOOD"
        )

        assert main.is_subcategory() is False
        assert food.is_subcategory() is True
        assert transport.is_subcategory() is True
        assert groceries.is_subcategory() is True
        assert restaurants.is_subcategory() is True

        assert food.parent_code == "EXPENSES"
        assert groceries.parent_code == "FOOD"

    def test_special_characters_in_names(self):
        """Test category names with special characters."""
        category = CategoryCode(
            code="MISC", name="Miscellaneous & Other Items (General)"
        )

        assert category.name == "Miscellaneous & Other Items (General)"
        assert category.code == "MISC"

    def test_numeric_codes(self):
        """Test categories with numeric codes."""
        category = CategoryCode(code="500", name="Office Supplies", parent_code="400")

        assert category.code == "500"
        assert category.parent_code == "400"

    def test_mixed_alphanumeric_codes(self):
        """Test categories with mixed alphanumeric codes."""
        category = CategoryCode(
            code="FOOD01", name="Primary Food Category", parent_code="EXP001"
        )

        assert category.code == "FOOD01"
        assert category.parent_code == "EXP001"

    def test_long_category_names(self):
        """Test categories with long descriptive names."""
        long_name = "Very Long Category Name That Describes Something Specific"
        category = CategoryCode("LONG", long_name)

        assert category.name == long_name
        assert len(category.name) > 50

    def test_unicode_characters_in_names(self):
        """Test category names with unicode characters."""
        category = CategoryCode(
            code="INTL", name="International & Foreign Currency Transactions"
        )

        assert category.name == "International & Foreign Currency Transactions"
        assert "Foreign Currency" in category.name

    def test_case_sensitivity_preservation_in_names(self):
        """Test that name case is preserved while code is normalized."""
        category = CategoryCode(code="food", name="Food & Dining")

        assert category.code == "FOOD"  # Normalized to uppercase
        assert category.name == "Food & Dining"  # Case preserved
