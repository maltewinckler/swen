"""Account anchor embedding endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from swen_ml_contracts import EmbedAccountsRequest, EmbedAccountsResponse

from swen_ml.storage import RepositoryFactory, get_session
from swen_ml.training import AccountEmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/users/{user_id}/accounts/embed", response_model=EmbedAccountsResponse)
async def embed_accounts(
    user_id: UUID,
    request: EmbedAccountsRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
) -> EmbedAccountsResponse:
    """Compute and store anchor embeddings for accounts."""
    encoder = http_request.app.state.encoder

    if not request.accounts:
        return EmbedAccountsResponse(embedded=0, message="No accounts provided")

    # Create service from factory
    repos = RepositoryFactory(session, user_id)
    service = AccountEmbeddingService.from_factory(encoder, repos)

    # Embed accounts
    embedded_count = await service.embed_accounts(request.accounts)

    logger.info(
        "Embedded %d account anchors for user %s",
        embedded_count,
        user_id,
    )

    return EmbedAccountsResponse(
        embedded=embedded_count,
        message=f"Embedded {embedded_count} account anchors",
    )


@router.delete("/users/{user_id}/accounts/{account_id}/embed")
async def delete_account_anchor(
    user_id: UUID,
    account_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Delete anchor embedding for a specific account."""
    encoder = http_request.app.state.encoder
    repos = RepositoryFactory(session, user_id)
    service = AccountEmbeddingService.from_factory(encoder, repos)

    deleted = await service.delete_account(account_id)

    logger.info(
        "Delete anchor request for user=%s, account=%s, deleted=%s",
        user_id,
        account_id,
        deleted,
    )

    return {"deleted": deleted}


@router.delete("/users/{user_id}/accounts/embed")
async def delete_all_anchors(
    user_id: UUID,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """Delete all anchor embeddings for a user."""
    encoder = http_request.app.state.encoder
    repos = RepositoryFactory(session, user_id)
    service = AccountEmbeddingService.from_factory(encoder, repos)
    count = await service.delete_all()

    logger.info("Delete all anchors for user=%s, count=%d", user_id, count)

    return {"deleted_count": count}
