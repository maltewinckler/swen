import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from swen.application.accounting.commands import (
    CreateAccountCommand,
    DeactivateAccountCommand,
    DeleteAccountCommand,
    ReactivateAccountCommand,
    UpdateAccountCommand,
)
from swen.application.accounting.dtos import (
    AccountSummaryDTO,
    CreateAccountDTO,
    UpdateAccountDTO,
)
from swen.application.accounting.queries import (
    AccountStatsQuery,
    ListAccountsQuery,
)
from swen.presentation.api.accounting.schemas.accounts import (
    AccountCreateRequest,
    AccountListResponse,
    AccountStatsResponse,
    AccountSummaryResponse,
    AccountUpdateRequest,
)
from swen.presentation.api.dependencies import MLClient, RepoFactory

logger = logging.getLogger(__name__)

router = APIRouter()

# Type aliases for query parameters using Annotated (modern FastAPI pattern)
AccountTypeFilter = Annotated[
    str | None,
    Query(description="Filter by type: asset, liability, equity, income, expense"),
]
ActiveOnlyFilter = Annotated[
    bool,
    Query(description="Only return active accounts"),
]

StatsIncludeDrafts = Annotated[
    bool,
    Query(description="Include draft transactions in statistics"),
]
StatsPeriodDays = Annotated[
    int | None,
    Query(description="Number of days for flow stats (null = all-time)", ge=1, le=3650),
]


def _to_account_response(dto: AccountSummaryDTO) -> AccountSummaryResponse:
    return AccountSummaryResponse.model_validate(dto)


@router.get(
    "",
    summary="List accounts",
    responses={
        200: {"description": "List of accounts"},
    },
)
async def list_accounts(
    factory: RepoFactory,
    account_type: AccountTypeFilter = None,
    active_only: ActiveOnlyFilter = True,
) -> AccountListResponse:
    """
    List all accounts for the current user.

    Supports filtering by account type and active status.
    """
    query = ListAccountsQuery.from_factory(factory)
    result = await query.execute(
        account_type=account_type,
        active_only=active_only,
    )

    return AccountListResponse.model_validate(result)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create account",
    responses={
        201: {"description": "Account created"},
        400: {"description": "Invalid input"},
        409: {"description": "Account already exists"},
    },
)
async def create_account(
    request: AccountCreateRequest,
    factory: RepoFactory,
    ml_client: MLClient,
) -> AccountSummaryResponse:
    """
    Create a new account in the chart of accounts.

    Account types: asset, liability, equity, income, expense
    """
    command = CreateAccountCommand.from_factory(factory, ml_client=ml_client)
    account = await command.execute(CreateAccountDTO(**request.model_dump()))

    logger.info("Account created: %s (%s)", account.name, account.account_number)

    # Convert domain entity to response (command returns entity for internal use)
    return _to_account_response(AccountSummaryDTO.from_entity(account))


@router.get(
    "/{account_id}",
    summary="Get account by ID",
    responses={
        200: {"description": "Account details"},
        404: {"description": "Account not found"},
    },
)
async def get_account(
    account_id: UUID,
    factory: RepoFactory,
) -> AccountSummaryResponse:
    """Get a specific account by ID."""
    query = ListAccountsQuery.from_factory(factory)
    dto = await query.find_by_id(account_id)

    if dto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return _to_account_response(dto)


@router.get(
    "/{account_id}/stats",
    summary="Get account statistics",
    responses={
        200: {"description": "Account statistics"},
        404: {"description": "Account not found"},
    },
)
async def get_account_stats(
    account_id: UUID,
    factory: RepoFactory,
    days: StatsPeriodDays = None,
    include_drafts: StatsIncludeDrafts = True,
) -> AccountStatsResponse:
    """
    Get comprehensive statistics for a specific account.

    Returns balance, transaction counts, and flow data for the account.

    **Parameters:**
    - `days`: Number of days to include in flow statistics (debits, credits, net_flow).
              If not specified, includes all-time statistics.
    - `include_drafts`: Whether to include draft (unposted) transactions in
                        calculations. Defaults to True for a complete picture.

    **Response includes:**
    - Current balance
    - Transaction counts (total, posted, draft)
    - Flow statistics (debits, credits, net flow) for the specified period
    - First and last transaction dates
    """
    query = AccountStatsQuery.from_factory(factory)

    # Exceptions are handled by the global exception handler
    stats = await query.execute(
        account_id=account_id,
        days=days,
        include_drafts=include_drafts,
    )

    return AccountStatsResponse.model_validate(stats)


@router.patch(
    "/{account_id}",
    summary="Update account",
    responses={
        200: {"description": "Account updated"},
        404: {"description": "Account not found"},
        409: {"description": "Name already exists"},
    },
)
async def update_account(
    account_id: UUID,
    request: AccountUpdateRequest,
    factory: RepoFactory,
    ml_client: MLClient,
) -> AccountSummaryResponse:
    """Update an account (name, account_number, description, and/or parent).

    Use parent_action to control parent relationship:
    - 'keep' (default): Don't change parent
    - 'set': Set parent to parent_id (requires parent_id)
    - 'remove': Remove parent, make top-level
    """
    command = UpdateAccountCommand.from_factory(factory, ml_client=ml_client)
    account = await command.execute(
        UpdateAccountDTO(account_id=account_id, **request.model_dump()),
    )

    logger.info("Account updated: %s", account.id)

    return _to_account_response(AccountSummaryDTO.from_entity(account))


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate account",
    responses={
        204: {"description": "Account deactivated"},
        404: {"description": "Account not found"},
    },
)
async def deactivate_account(
    account_id: UUID,
    factory: RepoFactory,
    ml_client: MLClient,
) -> None:
    """
    Deactivate an account (soft delete).

    The account is marked as inactive but not removed from the database.
    """
    command = DeactivateAccountCommand.from_factory(factory, ml_client=ml_client)
    await command.execute(account_id=account_id)

    logger.info("Account deactivated: %s", account_id)


@router.post(
    "/{account_id}/reactivate",
    summary="Reactivate account",
    responses={
        200: {"description": "Account reactivated"},
        404: {"description": "Account not found"},
    },
)
async def reactivate_account(
    account_id: UUID,
    factory: RepoFactory,
    ml_client: MLClient,
) -> AccountSummaryResponse:
    """
    Reactivate a previously deactivated account.

    The account will become visible in account lists and usable again.
    """
    command = ReactivateAccountCommand.from_factory(factory, ml_client=ml_client)
    account = await command.execute(account_id=account_id)

    logger.info("Account reactivated: %s", account_id)

    return _to_account_response(AccountSummaryDTO.from_entity(account))


@router.delete(
    "/{account_id}/permanent",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete account permanently",
    responses={
        204: {"description": "Account deleted permanently"},
        404: {"description": "Account not found"},
        422: {
            "description": "Account cannot be deleted (has transactions or children)"
        },
    },
)
async def delete_account(
    account_id: UUID,
    factory: RepoFactory,
    ml_client: MLClient,
) -> None:
    """
    Permanently delete an account.

    This is a hard delete - the account will be removed from the database.
    Only accounts with no transactions and no child accounts can be deleted.
    For accounts with data, use deactivate instead (soft delete).
    """
    command = DeleteAccountCommand.from_factory(factory, ml_client=ml_client)
    await command.execute(account_id=account_id)

    logger.info("Account deleted permanently: %s", account_id)
