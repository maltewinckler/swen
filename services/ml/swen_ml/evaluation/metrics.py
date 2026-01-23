"""Evaluation metrics computation."""

from dataclasses import dataclass, field

from swen_ml_contracts import Classification


@dataclass
class EvaluationMetrics:
    """Computed evaluation metrics."""

    total: int = 0
    correct: int = 0
    fallback_count: int = 0
    by_tier: dict[str, dict[str, int]] = field(default_factory=dict)
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def accuracy(self) -> float:
        """Overall accuracy."""
        return self.correct / self.total if self.total > 0 else 0.0

    @property
    def fallback_rate(self) -> float:
        """Percentage of transactions falling back to default."""
        return self.fallback_count / self.total if self.total > 0 else 0.0

    @property
    def high_confidence_accuracy(self) -> float:
        """Accuracy for high-confidence predictions (≥0.7)."""
        high_conf = self.by_tier.get("_high_confidence", {"correct": 0, "total": 0})
        if high_conf["total"] == 0:
            return 0.0
        return high_conf["correct"] / high_conf["total"]


def compute_metrics(
    classifications: list[Classification],
    expected_accounts: list[str],
) -> EvaluationMetrics:
    """Compute evaluation metrics from classifications and ground truth."""
    metrics = EvaluationMetrics(total=len(classifications))

    # Initialize tier buckets
    metrics.by_tier = {
        "pattern": {"correct": 0, "total": 0},
        "example": {"correct": 0, "total": 0},
        "anchor": {"correct": 0, "total": 0},
        "nli": {"correct": 0, "total": 0},
        "fallback": {"correct": 0, "total": 0},
        "_high_confidence": {"correct": 0, "total": 0},
    }

    for clf, expected in zip(classifications, expected_accounts, strict=True):
        is_correct = clf.account_number == expected
        tier = clf.tier

        # Overall metrics
        if is_correct:
            metrics.correct += 1

        if tier == "fallback":
            metrics.fallback_count += 1

        # By tier
        if tier in metrics.by_tier:
            metrics.by_tier[tier]["total"] += 1
            if is_correct:
                metrics.by_tier[tier]["correct"] += 1

        # High confidence tracking
        if clf.confidence >= 0.7:
            metrics.by_tier["_high_confidence"]["total"] += 1
            if is_correct:
                metrics.by_tier["_high_confidence"]["correct"] += 1

        # By category
        if expected not in metrics.by_category:
            metrics.by_category[expected] = {"correct": 0, "total": 0}
        metrics.by_category[expected]["total"] += 1
        if is_correct:
            metrics.by_category[expected]["correct"] += 1

    return metrics


def tier_accuracy(metrics: EvaluationMetrics, tier: str) -> float:
    """Get accuracy for a specific tier."""
    tier_data = metrics.by_tier.get(tier, {"correct": 0, "total": 0})
    if tier_data["total"] == 0:
        return 0.0
    return tier_data["correct"] / tier_data["total"]


def category_accuracy(metrics: EvaluationMetrics, category: str) -> float:
    """Get accuracy for a specific category."""
    cat_data = metrics.by_category.get(category, {"correct": 0, "total": 0})
    if cat_data["total"] == 0:
        return 0.0
    return cat_data["correct"] / cat_data["total"]
