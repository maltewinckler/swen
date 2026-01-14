"""Tests for AI Counter-Account value objects."""

from uuid import uuid4

import pytest

from swen.domain.integration.value_objects import (
    AICounterAccountResult,
    CounterAccountOption,
)


class TestAICounterAccountResult:
    """Test cases for AICounterAccountResult value object."""

    def test_create_valid_result(self):
        """Test creating a valid AI result."""
        account_id = uuid4()
        result = AICounterAccountResult(
            counter_account_id=account_id,
            confidence=0.85,
            reasoning="Transaction from REWE indicates grocery purchase",
        )

        assert result.counter_account_id == account_id
        assert result.confidence == 0.85
        assert result.reasoning == "Transaction from REWE indicates grocery purchase"

    def test_create_result_without_reasoning(self):
        """Test creating result without optional reasoning."""
        account_id = uuid4()
        result = AICounterAccountResult(
            counter_account_id=account_id,
            confidence=0.75,
        )

        assert result.counter_account_id == account_id
        assert result.confidence == 0.75
        assert result.reasoning is None

    def test_confidence_minimum_boundary(self):
        """Test that confidence of 0.0 is valid."""
        result = AICounterAccountResult(
            counter_account_id=uuid4(),
            confidence=0.0,
        )
        assert result.confidence == 0.0

    def test_confidence_maximum_boundary(self):
        """Test that confidence of 1.0 is valid."""
        result = AICounterAccountResult(
            counter_account_id=uuid4(),
            confidence=1.0,
        )
        assert result.confidence == 1.0

    def test_confidence_below_zero_raises_error(self):
        """Test that negative confidence raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            AICounterAccountResult(
                counter_account_id=uuid4(),
                confidence=-0.1,
            )

    def test_confidence_above_one_raises_error(self):
        """Test that confidence > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            AICounterAccountResult(
                counter_account_id=uuid4(),
                confidence=1.1,
            )

    def test_is_confident_default_threshold(self):
        """Test is_confident with default threshold of 0.7."""
        high_confidence = AICounterAccountResult(
            counter_account_id=uuid4(),
            confidence=0.85,
        )
        low_confidence = AICounterAccountResult(
            counter_account_id=uuid4(),
            confidence=0.5,
        )
        boundary_confidence = AICounterAccountResult(
            counter_account_id=uuid4(),
            confidence=0.7,
        )

        assert high_confidence.is_confident() is True
        assert low_confidence.is_confident() is False
        assert boundary_confidence.is_confident() is True  # >= threshold

    def test_is_confident_custom_threshold(self):
        """Test is_confident with custom threshold."""
        result = AICounterAccountResult(
            counter_account_id=uuid4(),
            confidence=0.6,
        )

        assert result.is_confident(threshold=0.5) is True
        assert result.is_confident(threshold=0.6) is True
        assert result.is_confident(threshold=0.7) is False
        assert result.is_confident(threshold=0.9) is False

    def test_immutability(self):
        """Test that AICounterAccountResult is immutable."""
        result = AICounterAccountResult(
            counter_account_id=uuid4(),
            confidence=0.8,
        )

        with pytest.raises(AttributeError):
            result.confidence = 0.9  # type: ignore


class TestCounterAccountOption:
    """Test cases for CounterAccountOption value object."""

    def test_create_expense_option(self):
        """Test creating an expense account option."""
        account_id = uuid4()
        option = CounterAccountOption(
            account_id=account_id,
            account_number="4000",
            name="Lebensmittel (Groceries)",
            account_type="expense",
        )

        assert option.account_id == account_id
        assert option.account_number == "4000"
        assert option.name == "Lebensmittel (Groceries)"
        assert option.account_type == "expense"

    def test_create_income_option(self):
        """Test creating an income account option."""
        account_id = uuid4()
        option = CounterAccountOption(
            account_id=account_id,
            account_number="3000",
            name="Gehälter (Salaries)",
            account_type="income",
        )

        assert option.account_id == account_id
        assert option.account_number == "3000"
        assert option.name == "Gehälter (Salaries)"
        assert option.account_type == "income"

    def test_invalid_account_type_raises_error(self):
        """Test that invalid account_type raises ValueError."""
        with pytest.raises(ValueError, match="account_type must be one of"):
            CounterAccountOption(
                account_id=uuid4(),
                account_number="1000",
                name="Bank Account",
                account_type="asset",  # Invalid - only expense/income allowed
            )

    def test_invalid_account_type_liability(self):
        """Test that liability type raises ValueError."""
        with pytest.raises(ValueError, match="account_type must be one of"):
            CounterAccountOption(
                account_id=uuid4(),
                account_number="2000",
                name="Loan",
                account_type="liability",
            )

    def test_display_label(self):
        """Test display_label property."""
        option = CounterAccountOption(
            account_id=uuid4(),
            account_number="4000",
            name="Lebensmittel (Groceries)",
            account_type="expense",
        )

        assert option.display_label == "[4000] Lebensmittel (Groceries)"

    def test_display_label_with_long_name(self):
        """Test display_label with a long account name."""
        option = CounterAccountOption(
            account_id=uuid4(),
            account_number="4100",
            name="Büromaterial und Schreibwaren (Office Supplies)",
            account_type="expense",
        )

        assert option.display_label == "[4100] Büromaterial und Schreibwaren (Office Supplies)"

    def test_description_optional(self):
        """Test that description is optional and defaults to None."""
        option = CounterAccountOption(
            account_id=uuid4(),
            account_number="4000",
            name="Groceries",
            account_type="expense",
        )
        assert option.description is None

    def test_description_provided(self):
        """Test that description can be provided."""
        option = CounterAccountOption(
            account_id=uuid4(),
            account_number="4000",
            name="Lebensmittel",
            account_type="expense",
            description="Supermarkets, groceries: REWE, Lidl, EDEKA",
        )
        assert option.description == "Supermarkets, groceries: REWE, Lidl, EDEKA"

    def test_display_label_with_description_no_description(self):
        """Test display_label_with_description without description."""
        option = CounterAccountOption(
            account_id=uuid4(),
            account_number="4000",
            name="Groceries",
            account_type="expense",
        )
        assert option.display_label_with_description == "[4000] Groceries (EXPENSE)"

    def test_display_label_with_description_has_description(self):
        """Test display_label_with_description with description."""
        option = CounterAccountOption(
            account_id=uuid4(),
            account_number="4000",
            name="Lebensmittel",
            account_type="expense",
            description="Supermarkets: REWE, Lidl, EDEKA",
        )
        expected = "[4000] Lebensmittel (EXPENSE)\n  → Supermarkets: REWE, Lidl, EDEKA"
        assert option.display_label_with_description == expected

    def test_immutability(self):
        """Test that CounterAccountOption is immutable."""
        option = CounterAccountOption(
            account_id=uuid4(),
            account_number="4000",
            name="Groceries",
            account_type="expense",
        )

        with pytest.raises(AttributeError):
            option.name = "Changed"  # type: ignore

    def test_equality(self):
        """Test equality comparison (frozen dataclass)."""
        account_id = uuid4()
        option1 = CounterAccountOption(
            account_id=account_id,
            account_number="4000",
            name="Groceries",
            account_type="expense",
        )
        option2 = CounterAccountOption(
            account_id=account_id,
            account_number="4000",
            name="Groceries",
            account_type="expense",
        )

        assert option1 == option2

    def test_hashable(self):
        """Test that CounterAccountOption can be used in sets."""
        option1 = CounterAccountOption(
            account_id=uuid4(),
            account_number="4000",
            name="Groceries",
            account_type="expense",
        )
        option2 = CounterAccountOption(
            account_id=uuid4(),
            account_number="4100",
            name="Utilities",
            account_type="expense",
        )

        option_set = {option1, option2}
        assert len(option_set) == 2

