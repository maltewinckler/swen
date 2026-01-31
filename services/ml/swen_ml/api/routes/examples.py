"""Example storage endpoint."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from swen_ml_contracts import StoreExampleRequest, StoreExampleResponse

from swen_ml.storage import RepositoryFactory, get_session
from swen_ml.training import ExampleEmbeddingService

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

    # Create service from factory
    repos = RepositoryFactory(session, user_id)
    service = ExampleEmbeddingService.from_factory(encoder, repos)

    # Store example
    total = await service.store_example(
        counterparty_name=request.counterparty_name,
        purpose=request.purpose,
        account_id=request.account_id,
        account_number=request.account_number,
    )

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
