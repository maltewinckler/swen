"""Batch classification endpoint."""

import logging
import time
from collections import Counter

from fastapi import APIRouter, Request
from swen_ml_contracts import (
    Classification,
    ClassificationStats,
    ClassifyBatchRequest,
    ClassifyBatchResponse,
)

from swen_ml.config.settings import get_settings
from swen_ml.pipeline.orchestrator import classify_batch

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/classify/batch", response_model=ClassifyBatchResponse)
async def classify_transactions(
    request: ClassifyBatchRequest,
    http_request: Request,
) -> ClassifyBatchResponse:
    """Classify a batch of transactions."""
    start_time = time.perf_counter()
    settings = get_settings()

    logger.info(
        "POST /classify/batch: user=%s, transactions=%d, accounts=%d",
        request.user_id,
        len(request.transactions),
        len(request.available_accounts),
    )

    # Log transaction details at debug level
    for i, txn in enumerate(request.transactions):
        logger.debug(
            "  TX[%d] id=%s amount=%.2f date=%s",
            i, txn.transaction_id, float(txn.amount), txn.booking_date,
        )
        logger.debug(
            "         counterparty=%r iban=%s",
            txn.counterparty_name, txn.counterparty_iban,
        )
        logger.debug(
            "         purpose=%r",
            txn.purpose,
        )

    encoder = http_request.app.state.encoder
    nli = http_request.app.state.nli

    classifications = await classify_batch(
        transactions=request.transactions,
        accounts=request.available_accounts,
        user_id=request.user_id,
        encoder=encoder,
        nli=nli,
        data_dir=settings.data_dir,
    )

    stats = _compute_stats(classifications)
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)

    # Log classification results per transaction
    for i, clf in enumerate(classifications):
        logger.debug(
            "  RESULT[%d] -> account=%s tier=%s conf=%.2f merchant=%r recurring=%s",
            i,
            clf.account_number,
            clf.tier,
            clf.confidence,
            clf.merchant,
            clf.is_recurring,
        )

    logger.info(
        "Classification complete: %d transactions in %dms, tiers=%s",
        len(classifications),
        elapsed_ms,
        stats.by_tier,
    )

    return ClassifyBatchResponse(
        classifications=classifications,
        stats=stats,
        processing_time_ms=elapsed_ms,
    )


def _compute_stats(classifications: list[Classification]) -> ClassificationStats:
    """Compute classification statistics."""
    tier_counts: dict[str, int] = dict(Counter(c.tier for c in classifications))

    confidence_buckets: dict[str, int] = dict(
        Counter(
            "high" if c.confidence >= 0.85 else "medium" if c.confidence >= 0.5 else "low"
            for c in classifications
        )
    )

    return ClassificationStats(
        total=len(classifications),
        by_tier=tier_counts,  # type: ignore[arg-type]
        by_confidence=confidence_buckets,  # type: ignore[arg-type]
        recurring_detected=sum(1 for c in classifications if c.is_recurring),
        merchants_extracted=sum(1 for c in classifications if c.merchant),
    )
