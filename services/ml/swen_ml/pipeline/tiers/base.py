"""Base types for classification tiers."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

TierName = Literal["pattern", "example", "anchor", "nli", "fallback"]


@dataclass
class TierResult:
    """Result from a classification tier."""

    account_number: str
    account_id: str
    confidence: float
    tier: TierName


@dataclass
class BatchTierResult:
    """Results from batch tier processing."""

    # Per-transaction results (None if tier didn't classify)
    results: list[TierResult | None]

    # Mask of which transactions were classified
    classified_mask: NDArray[np.bool_]

    @property
    def all_classified(self) -> bool:
        return bool(self.classified_mask.all())

    @property
    def unclassified_indices(self) -> NDArray[np.intp]:
        return np.where(~self.classified_mask)[0]
