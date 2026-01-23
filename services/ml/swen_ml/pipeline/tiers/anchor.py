"""Anchor retrieval tier for cold start (Tier 3)."""

import numpy as np
from numpy.typing import NDArray

from swen_ml.config.settings import get_settings
from swen_ml.pipeline.tiers.base import BatchTierResult, TierResult
from swen_ml.storage.anchor_store import AnchorStore


def anchor_retrieval_batch(
    embeddings: NDArray[np.float32],
    anchors: AnchorStore,
    already_classified: NDArray[np.bool_],
) -> BatchTierResult:
    """Match transactions against account description embeddings.

    Used for cold start when user has no examples.
    """
    settings = get_settings()
    n = len(embeddings)
    results: list[TierResult | None] = [None] * n
    classified = already_classified.copy()

    if len(anchors) == 0:
        return BatchTierResult(results=results, classified_mask=classified)

    # Get unclassified indices
    unclassified_idx = np.where(~already_classified)[0]
    if len(unclassified_idx) == 0:
        return BatchTierResult(results=results, classified_mask=classified)

    # Compute similarities
    unclassified_emb = embeddings[unclassified_idx]
    similarities = unclassified_emb @ anchors.embeddings.T

    # Get best match
    best_idx = np.argmax(similarities, axis=1)
    best_scores = np.max(similarities, axis=1)

    # Accept if above threshold
    accept = best_scores >= settings.anchor_accept_threshold

    for i, orig_idx in enumerate(unclassified_idx):
        if accept[i]:
            anchor_idx = best_idx[i]
            results[orig_idx] = TierResult(
                account_number=anchors.account_numbers[anchor_idx],
                account_id=anchors.account_ids[anchor_idx],
                confidence=float(best_scores[i]),
                tier="anchor",
            )
            classified[orig_idx] = True

    return BatchTierResult(results=results, classified_mask=classified)
