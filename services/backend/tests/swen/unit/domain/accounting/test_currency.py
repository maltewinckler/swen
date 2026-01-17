"""Tests for the Currency value object."""

import pytest
from pydantic import ValidationError

from swen.domain.accounting.value_objects import Currency
from swen.domain.accounting.value_objects.currency import (
    DEFAULT_CURRENCY,
    SUPPORTED_CURRENCIES,
)


class TestCurrency:
    """Test cases for Currency value object."""

    def test_currency_creation_valid_codes(self):
        """Test creating Currency with valid ISO codes."""
        eur = Currency(code="EUR")
        usd = Currency(code="USD")
        gbp = Currency(code="GBP")

        assert eur.code == "EUR"
        assert usd.code == "USD"
        assert gbp.code == "GBP"

    def test_currency_creation_lowercase_normalized(self):
        """Test that lowercase currency codes are normalized to uppercase."""
        eur = Currency(code="eur")
        usd = Currency(code="usd")

        assert eur.code == "EUR"
        assert usd.code == "USD"

    def test_currency_creation_with_spaces_trimmed(self):
        """Test that currency codes with spaces are trimmed."""
        eur = Currency(code="  EUR  ")
        usd = Currency(code=" USD ")

        assert eur.code == "EUR"
        assert usd.code == "USD"

    def test_default_currency(self):
        """Test default currency creation."""
        default = Currency.default()

        assert default.code == "EUR"
        assert isinstance(default, Currency)

    def test_from_string_factory_method(self):
        """Test creating Currency from string."""
        usd = Currency.from_string("USD")
        eur = Currency.from_string("eur")

        assert usd.code == "USD"
        assert eur.code == "EUR"

    def test_empty_currency_code_error(self):
        """Test that empty currency code raises ValueError."""
        with pytest.raises(ValueError, match="Currency code cannot be empty"):
            Currency("")

    def test_whitespace_only_currency_code_error(self):
        """Test that whitespace-only currency code raises ValueError."""
        with pytest.raises(ValueError, match="Currency code cannot be empty"):
            Currency(code="   ")

    def test_invalid_length_currency_code_error(self):
        """Test that currency codes not 3 characters raise ValueError."""
        with pytest.raises(ValueError, match="Currency code must be 3 characters long"):
            Currency(code="EU")

        with pytest.raises(ValueError, match="Currency code must be 3 characters long"):
            Currency(code="EURO")

    def test_non_alphabetic_currency_code_error(self):
        """Test that non-alphabetic currency codes raise ValueError."""
        with pytest.raises(ValueError, match="Currency code must contain only letters"):
            Currency("E12")

        with pytest.raises(ValueError, match="Currency code must contain only letters"):
            Currency("12D")

    def test_unsupported_currency_code_error(self):
        """Test that unsupported currency codes raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported currency code"):
            Currency(code="XYZ")

        with pytest.raises(ValueError, match="Unsupported currency code"):
            Currency(code="AAA")

    def test_supported_currencies(self):
        """Test that all major supported currencies work."""
        supported_currencies = [
            "EUR",
            "USD",
            "GBP",
            "CHF",
            "JPY",
            "CAD",
            "AUD",
            "SEK",
            "NOK",
            "DKK",
            "PLN",
            "CZK",
        ]

        for code in supported_currencies:
            currency = Currency(code)
            assert currency.code == code

    def test_currency_equality_with_currency(self):
        """Test currency equality with other Currency objects."""
        eur1 = Currency(code="EUR")
        eur2 = Currency(code="EUR")
        usd = Currency(code="USD")

        assert eur1 == eur2
        assert eur1 != usd
        assert eur2 != usd

    def test_currency_equality_with_string(self):
        """Test currency equality with string values."""
        eur = Currency(code="EUR")

        assert eur == "EUR"
        assert eur == "eur"  # Case insensitive
        assert eur != "USD"

    def test_currency_equality_with_other_types(self):
        """Test currency equality with non-Currency/string types."""
        eur = Currency(code="EUR")

        assert eur != 123
        assert eur is not None
        assert eur != []

    def test_currency_hashable(self):
        """Test that Currency is hashable for use in sets/dicts."""
        eur1 = Currency(code="EUR")
        eur2 = Currency(code="EUR")
        usd = Currency(code="USD")

        currency_set = {eur1, eur2, usd}
        assert len(currency_set) == 2  # eur1 and eur2 should be same

        currency_dict = {eur1: "Euro", usd: "Dollar"}
        assert len(currency_dict) == 2

    def test_currency_string_representation(self):
        """Test string representation of Currency."""
        eur = Currency(code="EUR")
        usd = Currency(code="USD")

        assert str(eur) == "EUR"
        assert str(usd) == "USD"

    def test_currency_immutability(self):
        """Test that Currency is immutable."""
        eur = Currency(code="EUR")

        with pytest.raises(ValidationError, match="frozen"):
            eur.code = "USD"

    def test_currency_in_collections(self):
        """Test Currency behavior in collections."""
        currencies = [Currency(code="EUR"), Currency(code="USD"), Currency(code="GBP")]

        # Test membership
        assert Currency(code="EUR") in currencies
        assert Currency(code="JPY") not in currencies

        # Test sorting (by code)
        sorted_currencies = sorted(currencies, key=lambda c: c.code)
        codes = [c.code for c in sorted_currencies]
        assert codes == ["EUR", "GBP", "USD"]

    def test_currency_case_insensitive_comparison(self):
        """Test that currency comparison is case insensitive for strings."""
        eur = Currency(code="EUR")

        assert eur == "EUR"
        assert eur == "eur"
        assert eur == "Eur"

    def test_comprehensive_supported_currencies(self):
        """Test all currencies in SUPPORTED_CURRENCIES constant."""
        for code in SUPPORTED_CURRENCIES:
            currency = Currency(code)
            assert currency.code == code
            assert len(currency.code) == 3
            assert currency.code.isalpha()

    def test_default_currency_constant(self):
        """Test that DEFAULT_CURRENCY constant works."""
        default = Currency.default()
        assert default.code == DEFAULT_CURRENCY
        assert DEFAULT_CURRENCY == "EUR"
