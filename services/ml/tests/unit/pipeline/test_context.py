"""Tests for ClassificationContext."""

from decimal import Decimal
from uuid import uuid4

from swen_ml.inference.pipeline import ClassificationContext


class TestClassificationContext:
    def test_expense_detection(self) -> None:
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="REWE Berlin",
            amount=Decimal("-50.00"),
        )
        assert ctx.is_expense is True
        assert ctx.is_income is False

    def test_income_detection(self) -> None:
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="Salary",
            amount=Decimal("3000.00"),
        )
        assert ctx.is_expense is False
        assert ctx.is_income is True

    def test_text_for_classification_uses_enhanced(self) -> None:
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="raw",
            amount=Decimal("-10.00"),
            cleaned_text="cleaned",
            enhanced_text="enhanced with keywords",
        )
        assert ctx.text_for_classification == "enhanced with keywords"

    def test_text_for_classification_falls_back_to_cleaned(self) -> None:
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="raw",
            amount=Decimal("-10.00"),
            cleaned_text="cleaned",
        )
        assert ctx.text_for_classification == "cleaned"

    def test_text_for_classification_falls_back_to_raw(self) -> None:
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="raw",
            amount=Decimal("-10.00"),
        )
        assert ctx.text_for_classification == "raw"

    def test_keywords_default_empty(self) -> None:
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="test",
            amount=Decimal("-10.00"),
        )
        assert ctx.keywords == []

    def test_metadata_default_empty(self) -> None:
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="test",
            amount=Decimal("-10.00"),
        )
        assert ctx.metadata == {}
