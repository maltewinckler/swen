"""Classification endpoints."""

from fastapi import APIRouter
from swen_ml_contracts import (
    ClassifyBatchRequest,
    ClassifyBatchResponse,
    ClassifyRequest,
    ClassifyResponse,
)

from swen_ml.api.dependencies import ClassifierDep

router = APIRouter(prefix="/classify", tags=["Classification"])


@router.post("", response_model=ClassifyResponse)
async def classify_transaction(
    request: ClassifyRequest, classifier: ClassifierDep
) -> ClassifyResponse:
    """Classify a single transaction using embedding similarity."""
    return classifier.classify(
        user_id=request.user_id,
        transaction=request.transaction,
        available_accounts=request.available_accounts,
    )


@router.post("/batch", response_model=ClassifyBatchResponse)
async def classify_batch(
    request: ClassifyBatchRequest, classifier: ClassifierDep
) -> ClassifyBatchResponse:
    """Classify multiple transactions in batch."""
    results, total_time_ms = classifier.classify_batch(
        user_id=request.user_id,
        transactions=request.transactions,
        available_accounts=request.available_accounts,
    )
    return ClassifyBatchResponse(results=results, total_inference_time_ms=total_time_ms)
