"""Example storage endpoint."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from swen_ml_contracts import StoreExampleRequest, StoreExampleResponse

from swen_ml.storage import ExampleRepository, get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/users/{user_id}/examples", response_model=StoreExampleResponse)
async def store_example(
    user_id: UUID,
    request: StoreExampleRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
) -> StoreExampleResponse:
    """Store a posted transaction as a training example."""
    encoder = http_request.app.state.encoder

    # Build text for embedding
    parts = []
    if request.counterparty_name:
        parts.append(request.counterparty_name)
    parts.append(request.purpose)
    text = " ".join(parts)

    # Encode (single text)
    embedding = encoder.encode([text])[0]

    # Store in database
    repo = ExampleRepository(session, user_id)
    await repo.add(
        embedding=embedding,
        account_id=str(request.account_id),
        account_number=request.account_number,
        text=text,
    )

    # Get total count
    total = await repo.count()

    logger.info(
        "Stored example for user=%s, account=%s, total=%d",
        user_id,
        request.account_number,
        total,
    )

    return StoreExampleResponse(
        stored=True,
        total_examples=total,
        message=f"Stored example for account {request.account_number}",
    )
