"""Account lifecycle endpoints."""

from uuid import UUID

from fastapi import APIRouter
from swen_ml_contracts import DeleteAccountResponse

from swen_ml.api.dependencies import ClassifierDep

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.delete("/{user_id}/{account_id}", response_model=DeleteAccountResponse)
async def delete_account(
    user_id: UUID, account_id: UUID, classifier: ClassifierDep
) -> DeleteAccountResponse:
    """Delete all embeddings for an account."""
    deleted = classifier.delete_account(user_id, account_id)
    return DeleteAccountResponse(
        deleted=True, examples_deleted=deleted, message=f"Deleted {deleted} examples"
    )
