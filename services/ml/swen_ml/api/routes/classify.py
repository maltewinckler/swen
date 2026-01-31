"""Batch classification endpoint."""

import logging
import time
from collections import Counter

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from swen_ml_contracts import (
    Classification,
    ClassificationStats,
    ClassificationTier,
    ClassifyBatchRequest,
    ClassifyBatchResponse,
)

from swen_ml.inference import ClassificationOrchestrator, ClassificationResult
from swen_ml.storage import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_classification(result: ClassificationResult) -> Classification:
    """Convert ClassificationResult to Classification contract model."""
    # Map resolved_by to tier
    tier: ClassificationTier
    if result.resolved_by == "example":
        tier = "example"
    elif result.resolved_by == "anchor":
        tier = "anchor"
    else:
        tier = "unresolved"

    return Classification(
        transaction_id=result.transaction_id,
        account_id=result.account_id,
        account_number=result.account_number,
        confidence=result.confidence,
        tier=tier,
        # TODO: Implement merchant extraction and recurring detection
        merchant=None,
        is_recurring=False,
        recurring_pattern=None,
    )


def _compute_stats(classifications: list[Classification]) -> ClassificationStats:
    """Compute classification statistics."""
    tier_counts: dict[str, int] = dict(Counter(c.tier for c in classifications))

    confidence_buckets: dict[str, int] = dict(
        Counter(
            "high"
            if c.confidence >= 0.85
            else "medium"
            if c.confidence >= 0.5
            else "low"
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


@router.post("/classify/batch", response_model=ClassifyBatchResponse)
async def classify_transactions(
    request: ClassifyBatchRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
) -> ClassifyBatchResponse:
    """Classify a batch of transactions."""
    start_time = time.perf_counter()
    logger.info(
        "POST /classify/batch: user=%s, transactions=%d",
        request.user_id,
        len(request.transactions),
    )

    # Get orchestrator from app state
    orchestrator: ClassificationOrchestrator = http_request.app.state.classification
    classification_results = await orchestrator.classify(
        session=session,
        transactions=request.transactions,
        user_id=request.user_id,
    )

    # Convert to Classification objects
    classifications = [_to_classification(result) for result in classification_results]
    stats = _compute_stats(classifications)
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
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
