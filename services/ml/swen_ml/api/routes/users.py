"""User management endpoints."""

from uuid import UUID

from fastapi import APIRouter
from swen_ml_contracts import DeleteUserResponse, UserStatsResponse

from swen_ml.api.dependencies import ClassifierDep

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(user_id: UUID, classifier: ClassifierDep) -> UserStatsResponse:
    """Get embedding stats for a user."""
    stats = classifier.get_user_stats(user_id)
    return UserStatsResponse(user_id=user_id, **stats)


@router.delete("/{user_id}", response_model=DeleteUserResponse)
async def delete_user(user_id: UUID, classifier: ClassifierDep) -> DeleteUserResponse:
    """Delete all embeddings for a user."""
    accounts, examples = classifier.delete_user(user_id)
    return DeleteUserResponse(
        deleted=True,
        accounts_deleted=accounts,
        examples_deleted=examples,
        message=f"Deleted {accounts} accounts, {examples} examples",
    )
