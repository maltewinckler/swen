"""Tests for the Money value object."""

from decimal import Decimal

import pytest

from swen.domain.accounting.value_objects import Currency, Money


class TestMoney:
    """Test cases for Money value object."""

    def test_money_creation(self):
        """Test basic Money creation."""
        money = Money(amount=Decimal("10.50"))

        assert money.amount == Decimal("10.50")
        assert money.currency == Currency(code="EUR")

    def test_money_creation_with_currency(self):
        """Test Money creation with specific currency."""
        # Test with string currency
        money1 = Money(amount=Decimal("25.50"), currency="USD")
        assert money1.amount == Decimal("25.50")
        assert money1.currency == Currency(code="USD")

        # Test with Currency object
        money2 = Money(amount=Decimal("30.75"), currency=Currency(code="GBP"))
        assert money2.amount == Decimal("30.75")
        assert money2.currency == Currency(code="GBP")

    def test_money_addition(self):
        """Test adding two Money instances."""
        money1 = Money(amount=Decimal("10.50"))
        money2 = Money(amount=Decimal("5.25"))
        result = money1 + money2
        assert result.amount == Decimal("15.75")
        assert result.currency == "EUR"

    def test_money_subtraction(self):
        """Test subtracting two Money instances."""
        money1 = Money(amount=Decimal("10.50"))
        money2 = Money(amount=Decimal("5.25"))
        result = money1 - money2
        assert result.amount == Decimal("5.25")
        assert result.currency == "EUR"

    def test_money_multiplication(self):
        """Test multiplying Money by a factor."""
        money = Money(amount=Decimal("10.00"))
        result = money * 2.5
        assert result.amount == Decimal("25.00")
        assert result.currency == "EUR"

    def test_money_comparison(self):
        """Test comparing Money instances."""
        money1 = Money(amount=Decimal("10.50"))
        money2 = Money(amount=Decimal("5.25"))
        money3 = Money(amount=Decimal("10.50"))

        assert money1 > money2
        assert money2 < money1
        assert money1 == money3

    def test_money_different_currencies_error(self):
        """Test that operations with different currencies raise error."""
        eur_money = Money(amount=Decimal("10.50"), currency="EUR")
        usd_money = Money(amount=Decimal("10.50"), currency="USD")

        with pytest.raises(ValueError, match="Cannot add different currencies"):
            _ = eur_money + usd_money

        with pytest.raises(ValueError, match="Cannot subtract different currencies"):
            _ = eur_money - usd_money

        with pytest.raises(ValueError, match="Cannot compare different currencies"):
            _ = eur_money < usd_money

    def test_money_predicates(self):
        """Test Money predicate methods."""
        zero = Money(amount=Decimal())
        positive = Money(amount=Decimal("10.50"))
        negative = Money(amount=Decimal("-5.25"))

        assert zero.is_zero()
        assert not zero.is_positive()
        assert not zero.is_negative()

        assert positive.is_positive()
        assert not positive.is_zero()
        assert not positive.is_negative()

        assert negative.is_negative()
        assert not negative.is_zero()
        assert not negative.is_positive()

    def test_money_abs(self):
        """Test absolute value of Money."""
        negative = Money(amount=Decimal("-10.50"))
        positive = Money(amount=Decimal("10.50"))

        assert negative.abs() == positive
        assert positive.abs() == positive

    def test_money_invalid_decimal_places(self):
        """Test that more than 2 decimal places raises error."""
        with pytest.raises(ValueError, match="Money cannot have more than 2 decimal places"):  # NOQA: E501
            Money(amount=Decimal("10.123"))

    def test_money_invalid_currency(self):
        """Test that invalid currency raises error."""
        with pytest.raises(ValueError, match="Currency code must be 3 characters long"):
            Money(amount=Decimal("10.50"), currency="EURO")

        with pytest.raises(ValueError, match="Currency code cannot be empty"):
            Money(amount=Decimal("10.50"), currency="")

    def test_money_string_representation(self):
        """Test string representation of Money."""
        money = Money(amount=Decimal("10.50"))
        assert str(money) == "10.50 EUR"

    def test_money_hashable(self):
        """Test that Money is hashable for use in sets/dicts."""
        money1 = Money(amount=Decimal("10.50"))
        money2 = Money(amount=Decimal("10.50"))
        money3 = Money(amount=Decimal("5.25"))

        money_set = {money1, money2, money3}
        assert len(money_set) == 2  # money1 and money2 are equal
