"""Tests for PipelineResult."""

from uuid import uuid4

from swen_ml.inference.pipeline import PipelineResult


class TestPipelineResult:
    def test_has_prediction_true(self) -> None:
        result = PipelineResult(
            account_id=uuid4(),
            account_number="4000",
            account_name="Lebensmittel",
            tier="pattern",
            confidence=1.0,
        )
        assert result.has_prediction is True

    def test_has_prediction_false(self) -> None:
        result = PipelineResult(
            account_id=None,
            account_number=None,
            account_name=None,
            tier="pattern",
            confidence=0.0,
        )
        assert result.has_prediction is False

    def test_keywords_default_empty(self) -> None:
        result = PipelineResult(
            account_id=uuid4(),
            account_number="4000",
            account_name="Test",
            tier="embedding",
            confidence=0.85,
        )
        assert result.keywords == []

    def test_optional_fields_default_none(self) -> None:
        result = PipelineResult(
            account_id=uuid4(),
            account_number="4000",
            account_name="Test",
            tier="zero_shot",
            confidence=0.6,
        )
        assert result.pattern_matched is None
        assert result.similar_transaction is None
        assert result.similarity_score is None
