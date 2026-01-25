"""Account anchor embedding endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from swen_ml_contracts import EmbedAccountsRequest, EmbedAccountsResponse

from swen_ml.storage import AnchorRepository, get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/users/{user_id}/accounts/embed", response_model=EmbedAccountsResponse)
async def embed_accounts(
    user_id: UUID,
    request: EmbedAccountsRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_session),
) -> EmbedAccountsResponse:
    """Compute and store anchor embeddings for accounts.

    This endpoint is additive - it upserts the provided accounts without
    affecting other existing anchors for the user.
    """
    encoder = http_request.app.state.encoder

    if not request.accounts:
        return EmbedAccountsResponse(embedded=0, message="No accounts provided")

    repo = AnchorRepository(session, user_id)

    # Process each account
    embedded_count = 0
    for account in request.accounts:
        # Build text from account name + description
        text = account.name
        if account.description:
            text = f"{account.name}: {account.description}"

        # Encode
        embedding = encoder.encode([text])[0]

        # Upsert into database
        await repo.upsert(
            account_id=account.account_id,
            embedding=embedding,
            account_number=account.account_number,
            name=account.name,
        )
        embedded_count += 1

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
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Delete anchor embedding for a specific account.

    Called when an account is deactivated or deleted.
    """
    repo = AnchorRepository(session, user_id)
    deleted = await repo.delete(account_id)

    if deleted:
        logger.info("Deleted anchor for user=%s, account=%s", user_id, account_id)
    else:
        logger.debug(
            "No anchor found to delete for user=%s, account=%s", user_id, account_id
        )

    return {"deleted": deleted}


@router.delete("/users/{user_id}/accounts/embed")
async def delete_all_anchors(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """Delete all anchor embeddings for a user.

    Used for cleanup when user is deleted.
    """
    repo = AnchorRepository(session, user_id)
    count = await repo.delete_all()

    if count > 0:
        logger.info("Deleted %d anchors for user %s", count, user_id)
    else:
        logger.debug("No anchors found for user %s", user_id)

    return {"deleted_count": count}
