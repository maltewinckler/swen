"""Tests for TextProcessor."""

from swen_ml.text.processor import TextProcessor


class TestClean:
    def test_removes_visa_debit(self) -> None:
        text = "VISA Debitkartenumsatz vom 15.01.2026 REWE Berlin"
        result = TextProcessor.clean(text)
        assert "VISA" not in result
        assert "REWE Berlin" in result

    def test_removes_lastschrift(self) -> None:
        text = "Lastschrift Stadtwerke Strom"
        result = TextProcessor.clean(text)
        assert "Lastschrift" not in result
        assert "Stadtwerke Strom" in result

    def test_removes_long_reference_numbers(self) -> None:
        text = "SPOTIFY 1234567890123 Stockholm"
        result = TextProcessor.clean(text)
        assert "1234567890123" not in result
        assert "SPOTIFY" in result
        assert "Stockholm" in result

    def test_removes_gmbh(self) -> None:
        text = "NaturStromHandel GmbH Strom Abschlag"
        result = TextProcessor.clean(text)
        assert "GmbH" not in result
        assert "NaturStromHandel" in result

    def test_collapses_whitespace(self) -> None:
        text = "REWE   Berlin    Einkauf"
        result = TextProcessor.clean(text)
        assert result == "REWE Berlin Einkauf"


class TestSplitCamelCase:
    def test_splits_camel_case(self) -> None:
        assert (
            TextProcessor.split_camel_case("NaturStromHandel") == "Natur Strom Handel"
        )

    def test_preserves_uppercase_words(self) -> None:
        assert TextProcessor.split_camel_case("REWE") == "REWE"

    def test_preserves_lowercase_words(self) -> None:
        assert TextProcessor.split_camel_case("spotify") == "spotify"


class TestNormalizeSeparators:
    def test_replaces_dots(self) -> None:
        assert TextProcessor.normalize_separators("REWE.Berlin") == "REWE Berlin"

    def test_replaces_slashes(self) -> None:
        assert TextProcessor.normalize_separators("REWE/Berlin") == "REWE Berlin"

    def test_replaces_multiple_dots(self) -> None:
        assert TextProcessor.normalize_separators("PAYPAL..HVV") == "PAYPAL HVV"


class TestExtractPaypalMerchant:
    def test_extracts_uber(self) -> None:
        text = "PAYPAL..UBERPAYMENT/35314369001"
        assert TextProcessor.extract_paypal_merchant(text) == "UBER"

    def test_extracts_hvv(self) -> None:
        text = "PAYPAL..HVV/35314369001"
        assert TextProcessor.extract_paypal_merchant(text) == "HVV"

    def test_extracts_spotify(self) -> None:
        text = "PAYPAL..SPOTIFY/12345"
        assert TextProcessor.extract_paypal_merchant(text) == "SPOTIFY"

    def test_returns_none_for_non_paypal(self) -> None:
        text = "REWE Berlin Einkauf"
        assert TextProcessor.extract_paypal_merchant(text) is None


class TestCleanForPatterns:
    def test_full_pipeline(self) -> None:
        text = "NaturStromHandel Lastschrift Strom Abschlag"
        result = TextProcessor.clean_for_patterns(text)
        # CamelCase split, banking noise removed, lowercased
        assert "natur" in result
        assert "strom" in result
        assert "handel" in result
        assert "lastschrift" not in result

    def test_paypal_transaction(self) -> None:
        text = "PAYPAL..HVV/35314369001"
        result = TextProcessor.clean_for_patterns(text)
        assert "paypal" in result
        assert "hvv" in result

    def test_restaurant_with_city(self) -> None:
        text = "Geile.Bar..Restaurant/Berlin"
        result = TextProcessor.clean_for_patterns(text)
        assert "bar" in result
        assert "restaurant" in result


class TestExtractKeywords:
    def test_extracts_words(self) -> None:
        text = "REWE Berlin Einkauf"
        keywords = TextProcessor.extract_keywords(text)
        assert "rewe" in keywords
        assert "berlin" in keywords
        assert "einkauf" in keywords
