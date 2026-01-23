"""Zero-shot NLI tier for disambiguation (Tier 4)."""

import logging

import numpy as np
from numpy.typing import NDArray
from swen_ml_contracts import AccountOption

from swen_ml.config.settings import get_settings
from swen_ml.models.nli import NLIClassifier
from swen_ml.pipeline.tiers.base import BatchTierResult, TierResult

logger = logging.getLogger(__name__)


def nli_disambiguation_batch(
    texts: list[str],
    accounts: list[AccountOption],
    nli: NLIClassifier,
    already_classified: NDArray[np.bool_],
) -> BatchTierResult:
    """Use NLI to classify remaining transactions.

    Only invoked for transactions that couldn't be classified by earlier tiers.
    """
    settings = get_settings()
    n = len(texts)
    results: list[TierResult | None] = [None] * n
    classified = already_classified.copy()

    # Get unclassified indices
    unclassified_idx = np.where(~already_classified)[0]
    if len(unclassified_idx) == 0:
        return BatchTierResult(results=results, classified_mask=classified)

    # Prepare texts and labels
    unclassified_texts = [texts[i] for i in unclassified_idx]
    labels = [a.name for a in accounts]

    # Guard: NLI requires at least one label
    if not labels:
        logger.warning("NLI skipped: no labels (accounts) provided")
        return BatchTierResult(results=results, classified_mask=classified)

    # Filter out empty texts (NLI requires non-empty sequences)
    valid_mask = [bool(t.strip()) for t in unclassified_texts]
    valid_idx = [i for i, valid in enumerate(valid_mask) if valid]
    valid_texts = [unclassified_texts[i] for i in valid_idx]

    n_empty = len(unclassified_texts) - len(valid_texts)
    if n_empty > 0:
        logger.warning(
            "NLI: filtered out %d empty texts, %d remaining",
            n_empty, len(valid_texts),
        )
        for i, t in enumerate(unclassified_texts):
            if not t.strip():
                orig_idx = unclassified_idx[i]
                logger.debug("  Index %d: empty text (will use fallback)", orig_idx)

    if not valid_texts:
        logger.warning("NLI skipped: all texts empty after filtering")
        return BatchTierResult(results=results, classified_mask=classified)

    # Run NLI classification
    scores = nli.classify(valid_texts, labels)

    # Get top-2 for margin computation
    top2_idx = np.argsort(-scores, axis=1)[:, :2]
    rows = np.arange(len(valid_texts))
    top1_scores = scores[rows, top2_idx[:, 0]]
    if scores.shape[1] > 1:
        top2_scores = scores[rows, top2_idx[:, 1]]
    else:
        top2_scores = np.zeros_like(top1_scores)
    margins = top1_scores - top2_scores

    # Accept if confident enough
    high_conf = top1_scores >= settings.nli_accept_threshold
    clear_winner = (top1_scores >= 0.45) & (margins >= settings.nli_margin_threshold)
    accept = high_conf | clear_winner

    # Map results back to original indices
    n_accepted = 0
    n_rejected = 0
    for i, local_idx in enumerate(valid_idx):
        orig_idx = int(unclassified_idx[local_idx])
        if accept[i]:
            best_account_idx = top2_idx[i, 0]
            account = accounts[best_account_idx]
            results[orig_idx] = TierResult(
                account_number=account.account_number,
                account_id=str(account.account_id),
                confidence=float(top1_scores[i]),
                tier="nli",
            )
            classified[orig_idx] = True
            n_accepted += 1
            logger.debug(
                "NLI classified idx=%d: %s (conf=%.3f, margin=%.3f)",
                orig_idx, account.name, top1_scores[i], margins[i],
            )
        else:
            n_rejected += 1
            logger.debug(
                "NLI rejected idx=%d: top_conf=%.3f, margin=%.3f (below threshold)",
                orig_idx, top1_scores[i], margins[i],
            )

    logger.info(
        "NLI results: %d accepted, %d rejected (thresholds: accept=%.2f, margin=%.2f)",
        n_accepted, n_rejected, settings.nli_accept_threshold, settings.nli_margin_threshold,
    )

    return BatchTierResult(results=results, classified_mask=classified)
