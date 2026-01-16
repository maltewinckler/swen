"""Accounts router for account management endpoints."""

import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from swen.application.commands.accounting import (
    ChartTemplate,
    CreateAccountCommand,
    DeactivateAccountCommand,
    DeleteAccountCommand,
    GenerateDefaultAccountsCommand,
    ParentAction,
    ReactivateAccountCommand,
    UpdateAccountCommand,
)
from swen.application.queries import (
    AccountStatsQuery,
    ListAccountsQuery,
    ReconciliationQuery,
)
from swen.application.services import BankAccountImportService
from swen.domain.shared.time import utc_now
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.accounts import (
    AccountCreateRequest,
    AccountListResponse,
    AccountReconciliationResponse,
    AccountResponse,
    AccountStatsResponse,
    AccountUpdateRequest,
    BankAccountListResponse,
    BankAccountRenameRequest,
    BankAccountResponse,
    ChartTemplateEnum,
    InitChartRequest,
    InitChartResponse,
    ReconciliationResponse,
)

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


def _get_created_at_or_now(created_at: datetime | None) -> datetime:
    """Get created_at timestamp, defaulting to now if None.

    The DTO may have None for created_at in some cases (e.g., legacy data),
    but the API response requires a non-null datetime.
    """
    return created_at if created_at is not None else utc_now()


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

    return AccountListResponse(
        accounts=[
            AccountResponse(
                id=UUID(dto.id),
                name=dto.name,
                account_number=dto.account_number,
                account_type=dto.account_type,
                description=dto.description,
                iban=dto.iban,
                currency=dto.currency,
                is_active=dto.is_active,
                created_at=_get_created_at_or_now(dto.created_at),
                parent_id=UUID(dto.parent_id) if dto.parent_id else None,
            )
            for dto in result.accounts
        ],
        total=result.total_count,
        by_type=result.by_type,
    )


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
) -> AccountResponse:
    """
    Create a new account in the chart of accounts.

    Account types: asset, liability, equity, income, expense
    """
    command = CreateAccountCommand.from_factory(factory)

    try:
        account = await command.execute(
            name=request.name,
            account_type=request.account_type,
            account_number=request.account_number,
            currency=request.currency,
            description=request.description,
            parent_id=request.parent_id,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Account created: %s (%s)", account.name, account.account_number)

    # Convert domain entity to response (command returns entity for internal use)
    return AccountResponse(
        id=account.id,
        name=account.name,
        account_number=account.account_number or "",
        account_type=account.account_type.value,
        description=account.description,
        iban=account.iban,
        currency=account.default_currency.code,
        is_active=account.is_active,
        created_at=account.created_at,
        parent_id=account.parent_id,
    )


@router.post(
    "/init-chart",
    status_code=status.HTTP_201_CREATED,
    summary="Initialize default chart of accounts",
    responses={
        201: {"description": "Default accounts created"},
        200: {"description": "Accounts already exist (skipped)"},
    },
)
async def init_chart_of_accounts(
    factory: RepoFactory,
    request: InitChartRequest | None = None,
) -> InitChartResponse:
    """
    Initialize the default chart of accounts for the current user.

    ## Template

    Creates a **minimal** chart of accounts with simple categories for
    everyday personal finance. ~15 accounts covering essentials:
    salary, rent, groceries, restaurants, transport, subscriptions, etc.

    ## Accounts Created

    - **Income accounts** (3xxx): Salary, Other Income
    - **Expense accounts** (4xxx): Rent, Utilities, Groceries, Restaurants, etc.
    - **Equity accounts** (2xxx): Opening Balance (required for bank sync)

    This is idempotent - if accounts already exist, it will return
    `skipped: true` instead of creating duplicates.

    **Note**: Asset accounts (bank accounts) are created automatically when
    you sync from a bank connection.
    """
    # Use minimal template if no request body provided
    template_enum = request.template if request else ChartTemplateEnum.MINIMAL

    # Convert API enum to domain enum
    template = ChartTemplate(template_enum.value)

    command = GenerateDefaultAccountsCommand.from_factory(factory)
    result = await command.execute(template=template)
    await factory.session.commit()

    if result.get("skipped"):
        logger.info("Chart of accounts already exists for user, skipped initialization")
        return InitChartResponse(
            message="Chart of accounts already exists",
            skipped=True,
            accounts_created=0,
            template=None,
            by_type=None,
        )

    logger.info(
        "Default chart of accounts initialized: %d accounts created (template: %s)",
        result["total"],
        template.value,
    )
    return InitChartResponse(
        message=f"Created {result['total']} default accounts",
        skipped=False,
        accounts_created=int(result["total"]),
        template=template.value,
        by_type={
            "income": int(result["INCOME"]),
            "expense": int(result["EXPENSE"]),
            "equity": int(result["EQUITY"]),
            "asset": int(result["ASSET"]),
            "liability": int(result["LIABILITY"]),
        },
    )


@router.get(
    "/bank",
    summary="List bank accounts",
    responses={
        200: {"description": "List of bank accounts with mappings"},
    },
)
async def list_bank_accounts(
    factory: RepoFactory,
) -> BankAccountListResponse:
    """
    List all imported bank accounts with their mapping information.

    These are accounts that have been imported from bank connections.
    """
    query = ListAccountsQuery.from_factory(factory)
    dtos = await query.list_bank_accounts()

    return BankAccountListResponse(
        accounts=[
            BankAccountResponse(
                id=UUID(dto.id),
                name=dto.name,
                account_number=dto.account_number,
                iban=dto.iban,
                currency=dto.currency,
                is_active=dto.is_active,
            )
            for dto in dtos
        ],
        total=len(dtos),
    )


@router.patch(
    "/bank/{iban}/rename",
    summary="Rename bank account",
    responses={
        200: {"description": "Bank account renamed"},
        404: {"description": "Bank account not found"},
    },
)
async def rename_bank_account(
    iban: str,
    request: BankAccountRenameRequest,
    factory: RepoFactory,
) -> BankAccountResponse:
    """
    Rename an imported bank account.

    Updates both the accounting account name and the account mapping.
    """
    import_service = BankAccountImportService.from_factory(factory)

    # Normalize IBAN (presentation concern - input sanitization)
    normalized_iban = iban.replace(" ", "").upper()

    try:
        dto = await import_service.rename_bank_account(
            iban=normalized_iban,
            new_name=request.name,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Bank account renamed: %s -> %s", normalized_iban, request.name)

    return BankAccountResponse(
        id=UUID(dto.id),
        name=dto.name,
        account_number=dto.account_number,
        iban=dto.iban,
        currency=dto.currency,
        is_active=dto.is_active,
    )


@router.get(
    "/reconciliation",
    summary="Reconcile bank balances with bookkeeping",
    responses={
        200: {"description": "Reconciliation results"},
    },
)
async def get_reconciliation(
    factory: RepoFactory,
) -> ReconciliationResponse:
    """
    Compare bank-reported balances with bookkeeping calculated balances.

    For each linked bank account, this endpoint:
    1. Gets the balance reported by the bank (from last sync)
    2. Calculates the balance from accounting transactions
    3. Reports any discrepancies

    Use this to verify that your bookkeeping matches your bank statements.
    A reconciled account means the balances match (within €0.01 tolerance).
    """
    query = ReconciliationQuery.from_factory(factory)
    result = await query.execute()

    return ReconciliationResponse(
        accounts=[
            AccountReconciliationResponse(
                iban=acc.iban,
                account_name=acc.account_name,
                accounting_account_id=acc.accounting_account_id,
                currency=acc.currency,
                bank_balance=str(acc.bank_balance),
                bank_balance_date=(
                    acc.bank_balance_date.isoformat() if acc.bank_balance_date else None
                ),
                last_sync_at=(
                    acc.last_sync_at.isoformat() if acc.last_sync_at else None
                ),
                bookkeeping_balance=str(acc.bookkeeping_balance),
                discrepancy=str(acc.discrepancy),
                is_reconciled=acc.is_reconciled,
            )
            for acc in result.accounts
        ],
        total_accounts=result.total_accounts,
        reconciled_count=result.reconciled_count,
        discrepancy_count=result.discrepancy_count,
        all_reconciled=result.all_reconciled,
    )


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
) -> AccountResponse:
    """Get a specific account by ID."""
    query = ListAccountsQuery.from_factory(factory)
    dto = await query.find_by_id(account_id)

    if dto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return AccountResponse(
        id=UUID(dto.id),
        name=dto.name,
        account_number=dto.account_number,
        account_type=dto.account_type,
        description=dto.description,
        iban=dto.iban,
        currency=dto.currency,
        is_active=dto.is_active,
        created_at=_get_created_at_or_now(dto.created_at),
        parent_id=UUID(dto.parent_id) if dto.parent_id else None,
    )


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

    return AccountStatsResponse(
        account_id=stats.account_id,
        account_name=stats.account_name,
        account_number=stats.account_number,
        account_type=stats.account_type,
        currency=stats.currency,
        balance=stats.balance,
        balance_includes_drafts=stats.balance_includes_drafts,
        transaction_count=stats.transaction_count,
        posted_count=stats.posted_count,
        draft_count=stats.draft_count,
        total_debits=stats.total_debits,
        total_credits=stats.total_credits,
        net_flow=stats.net_flow,
        first_transaction_date=(
            stats.first_transaction_date.isoformat()
            if stats.first_transaction_date
            else None
        ),
        last_transaction_date=(
            stats.last_transaction_date.isoformat()
            if stats.last_transaction_date
            else None
        ),
        period_days=stats.period_days,
        period_start=(stats.period_start.isoformat() if stats.period_start else None),
        period_end=stats.period_end.isoformat() if stats.period_end else None,
    )


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
) -> AccountResponse:
    """Update an account (name, account_number, description, and/or parent).

    Use parent_action to control parent relationship:
    - 'keep' (default): Don't change parent
    - 'set': Set parent to parent_id (requires parent_id)
    - 'remove': Remove parent, make top-level
    """
    command = UpdateAccountCommand.from_factory(factory)

    # Map API enum to application enum (same values, ensures decoupling)
    parent_action = ParentAction(request.parent_action.value)

    try:
        account = await command.execute(
            account_id=account_id,
            name=request.name,
            account_number=request.account_number,
            description=request.description,
            parent_id=request.parent_id,
            parent_action=parent_action,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Account updated: %s", account.id)

    return AccountResponse(
        id=account.id,
        name=account.name,
        account_number=account.account_number or "",
        account_type=account.account_type.value,
        description=account.description,
        iban=account.iban,
        currency=account.default_currency.code,
        is_active=account.is_active,
        created_at=account.created_at,
        parent_id=account.parent_id,
    )


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
) -> None:
    """
    Deactivate an account (soft delete).

    The account is marked as inactive but not removed from the database.
    """
    command = DeactivateAccountCommand.from_factory(factory)

    try:
        await command.execute(account_id=account_id)
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

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
) -> AccountResponse:
    """
    Reactivate a previously deactivated account.

    The account will become visible in account lists and usable again.
    """
    command = ReactivateAccountCommand.from_factory(factory)

    try:
        account = await command.execute(account_id=account_id)
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        raise

    logger.info("Account reactivated: %s", account_id)

    return AccountResponse(
        id=account.id,
        name=account.name,
        account_number=account.account_number or "",
        account_type=account.account_type.value,
        description=account.description,
        iban=account.iban,
        currency=account.default_currency.code,
        is_active=account.is_active,
        created_at=account.created_at,
        parent_id=account.parent_id,
    )


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
) -> None:
    """
    Permanently delete an account.

    This is a hard delete - the account will be removed from the database.
    Only accounts with no transactions and no child accounts can be deleted.
    For accounts with data, use deactivate instead (soft delete).
    """
    command = DeleteAccountCommand.from_factory(factory)

    try:
        await command.execute(account_id=account_id)
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        raise

    logger.info("Account deleted permanently: %s", account_id)
