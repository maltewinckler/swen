"""Example management endpoints."""

from fastapi import APIRouter
from swen_ml_contracts import (
    AddExampleRequest,
    AddExampleResponse,
    EmbedAccountsRequest,
    EmbedAccountsResponse,
)

from swen_ml.api.dependencies import ClassifierDep

router = APIRouter(tags=["Examples"])


@router.post("/examples", response_model=AddExampleResponse)
async def add_example(
    request: AddExampleRequest, classifier: ClassifierDep
) -> AddExampleResponse:
    """Add a posted transaction as an example for future classification."""
    total, text, was_added = classifier.add_example(
        user_id=request.user_id,
        account_id=request.account_id,
        purpose=request.purpose,
        amount=float(request.amount),
        counterparty_name=request.counterparty_name,
        reference=request.reference,
        transaction_id=request.transaction_id,
    )
    msg = f"Example added (total: {total})" if was_added else f"Duplicate skipped (total: {total})"
    return AddExampleResponse(
        stored=was_added, total_examples=total, message=msg, constructed_text=text
    )


@router.post("/accounts/embed", response_model=EmbedAccountsResponse)
async def embed_accounts(
    request: EmbedAccountsRequest, classifier: ClassifierDep
) -> EmbedAccountsResponse:
    """Embed account descriptions for cold-start classification."""
    embedded = classifier.embed_accounts(request.user_id, request.accounts)
    return EmbedAccountsResponse(embedded=embedded, message=f"Embedded {embedded} accounts")
