"""Batch classification orchestrator."""

import logging
from pathlib import Path
from uuid import UUID

from swen_ml_contracts import AccountOption, Classification, TransactionInput

from swen_ml.config.settings import get_settings
from swen_ml.models.encoder import Encoder
from swen_ml.models.nli import NLIClassifier
from swen_ml.pipeline.tiers.anchor import anchor_retrieval_batch
from swen_ml.pipeline.tiers.example import example_retrieval_batch
from swen_ml.pipeline.tiers.fallback import fallback_single
from swen_ml.pipeline.tiers.nli import nli_disambiguation_batch
from swen_ml.pipeline.tiers.pattern import pattern_match_batch
from swen_ml.preprocessing.merchant import extract_merchant
from swen_ml.preprocessing.noise_model import NoiseModel
from swen_ml.preprocessing.recurring import detect_recurring_batch
from swen_ml.storage.anchor_store import AnchorStore, get_anchor_path
from swen_ml.storage.example_store import ExampleStore, get_example_path
from swen_ml.storage.noise_store import (
    get_noise_path,
    load_noise_model_or_empty,
    save_noise_model,
)

logger = logging.getLogger(__name__)


async def classify_batch(
    transactions: list[TransactionInput],
    accounts: list[AccountOption],
    user_id: UUID,
    encoder: Encoder,
    nli: NLIClassifier,
    data_dir: Path | None = None,
) -> list[Classification]:
    """Classify a batch of transactions through the tiered pipeline.

    Pipeline phases:
    1. Build/update noise model from batch
    2. Extract merchants
    3. Pattern matching (known merchants/keywords)
    4. Example retrieval (user's posted transactions)
    5. Anchor retrieval (account descriptions)
    6. NLI disambiguation
    7. Fallback
    8. Recurring pattern detection
    """
    settings = get_settings()
    data_dir = data_dir or settings.data_dir
    n_txns = len(transactions)
    n_accounts = len(accounts)

    logger.info(
        "Starting batch classification: %d transactions, %d accounts, user=%s",
        n_txns, n_accounts, user_id,
    )

    # --- Phase 1: Noise model ---
    noise_model = _load_or_build_noise_model(transactions, user_id, data_dir)

    # Combine counterparty and purpose for embedding
    raw_texts = [_build_text(txn) for txn in transactions]
    cleaned_texts = noise_model.clean_batch(raw_texts)

    # Log text cleaning results
    empty_after_clean = sum(1 for t in cleaned_texts if not t.strip())
    if empty_after_clean > 0:
        logger.warning(
            "Noise model produced %d empty texts out of %d",
            empty_after_clean, n_txns,
        )
        for i, (raw, clean) in enumerate(zip(raw_texts, cleaned_texts)):
            if not clean.strip():
                logger.debug(
                    "  Transaction %d: raw=%r -> cleaned=%r (empty)",
                    i, raw[:100], clean,
                )

    # --- Phase 2: Extract merchants ---
    merchants = [extract_merchant(txn.counterparty_name) for txn in transactions]
    n_merchants = sum(1 for m in merchants if m)
    logger.debug("Extracted %d merchants from %d transactions", n_merchants, n_txns)

    # --- Phase 3: Pattern matching ---
    pattern_result = pattern_match_batch(transactions, accounts)
    classified = pattern_result.classified_mask.copy()
    n_pattern = int(classified.sum())
    logger.info("Pattern tier: %d/%d classified", n_pattern, n_txns)

    # --- Phase 4: Compute embeddings for unclassified ---
    embeddings = None
    if not classified.all():
        embeddings = encoder.encode(cleaned_texts)
        logger.debug("Computed embeddings for %d transactions", n_txns)

    # --- Phase 5: Example retrieval ---
    examples = ExampleStore.load_or_empty(get_example_path(data_dir, user_id))
    example_result = None
    if embeddings is not None and len(examples) > 0:
        example_result = example_retrieval_batch(embeddings, examples, classified)
        n_example = int(example_result.classified_mask.sum()) - n_pattern
        logger.info(
            "Example tier: %d additional classified (%d examples)",
            n_example, len(examples),
        )
        classified = example_result.classified_mask
    else:
        logger.debug(
            "Example tier skipped: embeddings=%s, examples=%d",
            embeddings is not None, len(examples),
        )

    # --- Phase 6: Anchor retrieval ---
    anchors = AnchorStore.load_or_empty(get_anchor_path(data_dir, user_id))
    anchor_result = None
    n_before_anchor = int(classified.sum())
    if embeddings is not None and len(anchors) > 0 and not classified.all():
        anchor_result = anchor_retrieval_batch(embeddings, anchors, classified)
        n_anchor = int(anchor_result.classified_mask.sum()) - n_before_anchor
        logger.info(
            "Anchor tier: %d additional classified (%d anchors)",
            n_anchor, len(anchors),
        )
        classified = anchor_result.classified_mask
    else:
        logger.debug("Anchor tier skipped: embeddings=%s, anchors=%d, all_classified=%s",
                     embeddings is not None, len(anchors), classified.all())

    # --- Phase 7: NLI disambiguation ---
    nli_result = None
    n_before_nli = int(classified.sum())
    n_unclassified = n_txns - n_before_nli
    if not classified.all() and accounts:
        logger.info("NLI tier: attempting to classify %d remaining transactions", n_unclassified)
        nli_result = nli_disambiguation_batch(cleaned_texts, accounts, nli, classified)
        n_nli = int(nli_result.classified_mask.sum()) - n_before_nli
        logger.info("NLI tier: %d additional classified", n_nli)
        classified = nli_result.classified_mask
    else:
        if not accounts:
            logger.warning("NLI tier skipped: no accounts provided")
        else:
            logger.debug("NLI tier skipped: all transactions already classified")

    # --- Phase 8: Recurring detection ---
    recurring = detect_recurring_batch(transactions)
    n_recurring = len(recurring)
    if n_recurring > 0:
        logger.info("Recurring detection: %d patterns found", n_recurring)

    # --- Build final results ---
    results: list[Classification] = []

    for i, txn in enumerate(transactions):
        tier_result = None

        # Find which tier classified this transaction
        if pattern_result.results[i]:
            tier_result = pattern_result.results[i]
        elif example_result and example_result.results[i]:
            tier_result = example_result.results[i]
        elif anchor_result and anchor_result.results[i]:
            tier_result = anchor_result.results[i]
        elif nli_result and nli_result.results[i]:
            tier_result = nli_result.results[i]
        else:
            tier_result = fallback_single(txn, accounts)

        # Build classification
        txn_id_str = str(txn.transaction_id)
        recurring_info = recurring.get(txn_id_str)

        # tier_result is guaranteed by fallback_single in else branch
        assert tier_result is not None

        results.append(
            Classification(
                transaction_id=txn.transaction_id,
                account_id=UUID(tier_result.account_id),
                account_number=tier_result.account_number,
                confidence=tier_result.confidence,
                tier=tier_result.tier,
                merchant=merchants[i],
                is_recurring=recurring_info is not None,
                recurring_pattern=recurring_info.pattern if recurring_info else None,
            )
        )

    # Log final tier distribution
    tier_counts: dict[str, int] = {}
    for r in results:
        tier_counts[r.tier] = tier_counts.get(r.tier, 0) + 1
    logger.info(
        "Classification complete: %d transactions -> %s",
        n_txns, tier_counts,
    )

    return results


def _build_text(txn: TransactionInput) -> str:
    """Combine transaction fields into text for embedding."""
    parts = []
    if txn.counterparty_name:
        parts.append(txn.counterparty_name)
    parts.append(txn.purpose)
    return " ".join(parts)


def _load_or_build_noise_model(
    transactions: list[TransactionInput],
    user_id: UUID,
    data_dir: Path,
) -> NoiseModel:
    """Load existing noise model or build from batch."""
    noise_path = get_noise_path(data_dir, user_id)
    noise_model = load_noise_model_or_empty(noise_path)

    # Update with new transactions
    texts = [_build_text(txn) for txn in transactions]
    noise_model.observe_batch(texts)

    # Persist updated model
    save_noise_model(noise_model, noise_path)

    return noise_model
