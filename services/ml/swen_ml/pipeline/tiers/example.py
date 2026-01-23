"""Example retrieval tier (Tier 2)."""

import numpy as np
from numpy.typing import NDArray

from swen_ml.config.settings import get_settings
from swen_ml.pipeline.tiers.base import BatchTierResult, TierResult
from swen_ml.storage.example_store import ExampleStore


def example_retrieval_batch(
    embeddings: NDArray[np.float32],
    examples: ExampleStore,
    already_classified: NDArray[np.bool_],
) -> BatchTierResult:
    """Match transactions against user's posted examples.

    Uses matrix multiplication for efficient batch similarity computation.
    """
    settings = get_settings()
    n = len(embeddings)
    results: list[TierResult | None] = [None] * n
    classified = already_classified.copy()

    if len(examples) == 0:
        return BatchTierResult(results=results, classified_mask=classified)

    # Get unclassified indices
    unclassified_idx = np.where(~already_classified)[0]
    if len(unclassified_idx) == 0:
        return BatchTierResult(results=results, classified_mask=classified)

    # Compute similarities for unclassified transactions only
    unclassified_emb = embeddings[unclassified_idx]

    # Matrix multiply: (U, dim) @ (M, dim).T = (U, M)
    similarities = unclassified_emb @ examples.embeddings.T

    # Get top-2 for margin computation
    top2_idx = np.argsort(-similarities, axis=1)[:, :2]
    rows = np.arange(len(unclassified_idx))
    top1_scores = similarities[rows, top2_idx[:, 0]]
    if similarities.shape[1] > 1:
        top2_scores = similarities[rows, top2_idx[:, 1]]
    else:
        top2_scores = np.zeros_like(top1_scores)
    margins = top1_scores - top2_scores

    # Apply decision logic
    high_conf = top1_scores >= settings.example_high_confidence
    clear_winner = (top1_scores >= settings.example_accept_threshold) & (
        margins >= settings.example_margin_threshold
    )
    accept = high_conf | clear_winner

    for i, orig_idx in enumerate(unclassified_idx):
        if accept[i]:
            best_example_idx = top2_idx[i, 0]
            results[orig_idx] = TierResult(
                account_number=examples.account_numbers[best_example_idx],
                account_id=examples.account_ids[best_example_idx],
                confidence=float(top1_scores[i]),
                tier="example",
            )
            classified[orig_idx] = True

    return BatchTierResult(results=results, classified_mask=classified)
