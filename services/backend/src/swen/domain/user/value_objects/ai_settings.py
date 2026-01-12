"""AI settings value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AISettings:
    """User's AI classification preferences."""

    enabled: bool = True
    model_name: str = "qwen2.5:3b"
    min_confidence: float = 0.7

    def with_enabled(self, enabled: bool) -> "AISettings":
        return AISettings(
            enabled=enabled,
            model_name=self.model_name,
            min_confidence=self.min_confidence,
        )

    def with_model(self, model_name: str) -> "AISettings":
        return AISettings(
            enabled=self.enabled,
            model_name=model_name,
            min_confidence=self.min_confidence,
        )

    def with_confidence(self, min_confidence: float) -> "AISettings":
        # Clamp to valid range
        clamped = max(0.0, min(1.0, min_confidence))
        return AISettings(
            enabled=self.enabled,
            model_name=self.model_name,
            min_confidence=clamped,
        )
