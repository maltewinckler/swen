"""Onboarding router for guiding new users through initial setup."""

import logging

from fastapi import APIRouter
from pydantic import ConfigDict

from swen.application.system.queries.onboarding import OnboardingStatusQuery
from swen.application.system.queries.onboarding.onboarding_status_query import (
    OnboardingStatusDTO,
)
from swen.presentation.api.dependencies import RepoFactory

logger = logging.getLogger(__name__)

router = APIRouter()


class OnboardingStatusResponse(OnboardingStatusDTO):
    """Onboarding status response."""

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/status",
    summary="Get onboarding status",
    responses={
        200: {"description": "Onboarding status for the current user"},
    },
)
async def get_onboarding_status(factory: RepoFactory) -> OnboardingStatusResponse:
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

    return OnboardingStatusResponse.model_validate(status)
