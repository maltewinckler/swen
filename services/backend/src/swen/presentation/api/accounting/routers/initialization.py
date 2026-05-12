"""Accounts router for account management endpoints."""

import logging

from fastapi import APIRouter, status

from swen.application.accounting.commands import (
    ChartTemplate,
    GenerateDefaultAccountsCommand,
)
from swen.presentation.api.accounting.schemas.accounts import (
    ChartTemplateEnum,
    InitChartRequest,
    InitChartResponse,
    InitEssentialsResponse,
)
from swen.presentation.api.dependencies import MLClient, RepoFactory

logger = logging.getLogger(__name__)

router = APIRouter()


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
    ml_client: MLClient,
    request: InitChartRequest | None = None,
) -> InitChartResponse:
    """
    Initialize the default chart of accounts for the current user.

    ## Template

    Creates a **minimal** chart of accounts with simple categories for
    everyday personal finance. ~13 accounts covering essentials:
    salary, housing, groceries, restaurants, transport, subscriptions, etc.

    ## Accounts Created

    - **Income accounts** (3xxx): Salary, Other Income
    - **Expense accounts** (4xxx): Housing, Groceries, Restaurants, etc.
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

    command = GenerateDefaultAccountsCommand.from_factory(factory, ml_client=ml_client)
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


@router.post(
    "/init-essentials",
    status_code=status.HTTP_201_CREATED,
    summary="Initialize essential accounts only",
    responses={
        201: {"description": "Essential accounts created"},
        200: {"description": "Essential accounts already exist (skipped)"},
    },
)
async def init_essential_accounts(
    factory: RepoFactory,
    ml_client: MLClient,
) -> InitEssentialsResponse:
    """
    Initialize only the essential accounts required for basic operation.

    Creates 3 accounts (if they don't exist):
    - **Bargeld** (1000): Cash asset account for cash transactions
    - **Sonstige Einnahmen** (3100): Fallback income account
    - **Sonstiges** (4900): Fallback expense account

    This is idempotent - existing accounts are skipped, not duplicated.
    Use this when users choose manual account setup but you still need
    the essential accounts for cash transactions and fallback categorization.
    """
    command = GenerateDefaultAccountsCommand.from_factory(factory, ml_client=ml_client)
    result = await command.execute_essentials()
    await factory.session.commit()

    if result["skipped"]:
        logger.info("Essential accounts already exist, skipped initialization")
        return InitEssentialsResponse(
            message="Essential accounts already exist",
            skipped=True,
            accounts_created=0,
        )

    logger.info(
        "Essential accounts initialized: %d created",
        result["accounts_created"],
    )
    return InitEssentialsResponse(
        message=f"Created {result['accounts_created']} essential accounts",
        skipped=False,
        accounts_created=int(result["accounts_created"]),
    )
