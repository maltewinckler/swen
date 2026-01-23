"""Tests for KeywordEnhancer."""

from decimal import Decimal
from uuid import uuid4

from swen_ml.inference.pipeline import ClassificationContext, KeywordEnhancer


class TestKeywordEnhancer:
    def test_enhances_spotify(self) -> None:
        enhancer = KeywordEnhancer()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="SPOTIFY Stockholm",
            amount=Decimal("-9.99"),
        )
        result = enhancer.enhance("SPOTIFY Stockholm", ctx)
        assert "Streaming" in result.keywords
        assert "Musik" in result.keywords
        assert result.source == "local"
        assert "SPOTIFY" in result.text
        assert "Streaming" in result.text

    def test_enhances_rewe(self) -> None:
        enhancer = KeywordEnhancer()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="REWE Berlin",
            amount=Decimal("-50.00"),
        )
        result = enhancer.enhance("REWE Berlin", ctx)
        assert "Supermarkt" in result.keywords
        assert "Lebensmittel" in result.keywords
        assert result.source == "local"

    def test_no_match_returns_original(self) -> None:
        enhancer = KeywordEnhancer()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="UNKNOWN XYZ",
            amount=Decimal("-10.00"),
        )
        result = enhancer.enhance("UNKNOWN XYZ", ctx)
        assert result.keywords == []
        assert result.source == "none"
        assert result.text == "UNKNOWN XYZ"

    def test_disabled_returns_original(self) -> None:
        enhancer = KeywordEnhancer(enabled=False)
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="REWE Berlin",
            amount=Decimal("-50.00"),
        )
        result = enhancer.enhance("REWE Berlin", ctx)
        assert result.keywords == []
        assert result.source == "none"
        assert result.text == "REWE Berlin"

    def test_deduplicates_keywords(self) -> None:
        enhancer = KeywordEnhancer()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="REWE Edeka",  # Both supermarkets
            amount=Decimal("-50.00"),
        )
        result = enhancer.enhance("REWE Edeka", ctx)
        # Should have deduplicated keywords
        assert len(result.keywords) == len(set(result.keywords))
