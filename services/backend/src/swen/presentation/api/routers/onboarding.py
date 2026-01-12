"""Onboarding router for guiding new users through initial setup."""

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from swen.application.queries.onboarding import OnboardingStatusQuery
from swen.presentation.api.dependencies import RepoFactory

logger = logging.getLogger(__name__)

router = APIRouter()

class CompletedStepsResponse(BaseModel):
    """Individual onboarding steps completion status."""

    accounts_initialized: bool
    first_bank_connected: bool
    has_transactions: bool

class OnboardingStatusResponse(BaseModel):
    """Onboarding status response."""

    needs_onboarding: bool
    completed_steps: CompletedStepsResponse

@router.get(
    "/status",
    summary="Get onboarding status",
    responses={
        200: {"description": "Onboarding status for the current user"},
    },
)
async def get_onboarding_status(
    factory: RepoFactory,
) -> OnboardingStatusResponse:
    """
    Get the onboarding status for the current user.

    The status is derived from existing data:
    - accounts_initialized: True if expense accounts exist
    - first_bank_connected: True if bank credentials exist
    - has_transactions: True if transactions exist

    The main trigger for onboarding is `needs_onboarding`, which is True
    if expense accounts haven't been initialized yet.
    """
    query = OnboardingStatusQuery.from_factory(factory)
    status = await query.execute()

    return OnboardingStatusResponse(
        needs_onboarding=status.needs_onboarding,
        completed_steps=CompletedStepsResponse(
            accounts_initialized=status.completed_steps.accounts_initialized,
            first_bank_connected=status.completed_steps.first_bank_connected,
            has_transactions=status.completed_steps.has_transactions,
        ),
    )
