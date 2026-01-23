"""Tests for protocol definitions."""

from decimal import Decimal
from uuid import uuid4

from swen_ml.inference.pipeline import (
    ClassificationContext,
    ClassificationTier,
    EnhancedText,
    PipelineResult,
    TextEnhancer,
)


class MockTier:
    """Mock implementation of ClassificationTier for testing."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    @property
    def name(self) -> str:
        return "mock"

    @property
    def enabled(self) -> bool:
        return self._enabled

    def classify(
        self,
        text: str,
        accounts: list,
        context: ClassificationContext,
    ) -> PipelineResult | None:
        if "match" in text:
            return PipelineResult(
                account_id=uuid4(),
                account_number="4000",
                account_name="Test",
                tier="pattern",
                confidence=1.0,
            )
        return None


class MockEnhancer:
    """Mock implementation of TextEnhancer for testing."""

    def __init__(self, *, enabled: bool = True) -> None:
        self._enabled = enabled

    @property
    def name(self) -> str:
        return "mock"

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enhance(
        self,
        text: str,
        context: ClassificationContext,
    ) -> EnhancedText:
        return EnhancedText(
            text=f"{text} enhanced",
            keywords=["test"],
            source="mock",
        )


class TestClassificationTierProtocol:
    def test_mock_tier_matches_protocol(self) -> None:
        tier: ClassificationTier = MockTier()
        assert tier.name == "mock"
        assert tier.enabled is True

    def test_tier_classify_returns_result(self) -> None:
        tier = MockTier()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="match this",
            amount=Decimal("-10.00"),
        )
        result = tier.classify("match this", [], ctx)
        assert result is not None
        assert result.tier == "pattern"

    def test_tier_classify_returns_none(self) -> None:
        tier = MockTier()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="unknown text",
            amount=Decimal("-10.00"),
        )
        result = tier.classify("unknown text", [], ctx)
        assert result is None


class TestTextEnhancerProtocol:
    def test_mock_enhancer_matches_protocol(self) -> None:
        enhancer: TextEnhancer = MockEnhancer()
        assert enhancer.name == "mock"
        assert enhancer.enabled is True

    def test_enhancer_returns_enhanced_text(self) -> None:
        enhancer = MockEnhancer()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="test",
            amount=Decimal("-10.00"),
        )
        result = enhancer.enhance("input", ctx)
        assert result.text == "input enhanced"
        assert result.keywords == ["test"]
        assert result.source == "mock"
