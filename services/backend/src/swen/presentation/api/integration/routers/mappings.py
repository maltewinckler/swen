"""Mappings router for bank account to ledger account mappings."""

import logging

from fastapi import APIRouter, HTTPException, status

from swen.application.integration.commands import CreateExternalAccountCommand
from swen.application.integration.queries import (
    ListAccountMappingsQuery,
)
from swen.domain.accounting.entities import AccountType
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.integration.schemas.mappings import (
    AccountMappingListResponse,
    AccountMappingResponse,
    ExternalAccountCreateRequest,
    ExternalAccountCreateResponse,
    ExternalAccountType,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    summary="List bank account mappings",
    responses={
        200: {"description": "List of bank account mappings"},
    },
)
async def list_mappings(factory: RepoFactory) -> AccountMappingListResponse:
    """
    List all bank account to ledger account mappings.

    These mappings connect imported bank accounts (identified by IBAN)
    to accounting accounts in your chart of accounts.

    Each mapping shows:
    - The bank account IBAN and name
    - The linked ledger account (for categorization)
    """
    query = ListAccountMappingsQuery.from_factory(factory)
    result = await query.execute()

    mappings = [
        AccountMappingResponse.model_validate(m.model_dump()) for m in result.mappings
    ]

    return AccountMappingListResponse(
        mappings=mappings,
        count=result.count,
    )


@router.get(
    "/{iban}",
    summary="Get mapping by IBAN",
    responses={
        200: {"description": "Bank account mapping"},
        404: {"description": "Mapping not found"},
    },
)
async def get_mapping_by_iban(
    iban: str,
    factory: RepoFactory,
) -> AccountMappingResponse:
    """
    Get a specific bank account mapping by IBAN.

    Use this to check which ledger account a bank account is mapped to.
    """
    query = ListAccountMappingsQuery.from_factory(factory)
    result = await query.get_by_iban(iban)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mapping found for IBAN: {iban}",
        )

    return AccountMappingResponse.model_validate(result.model_dump())


@router.post(
    "/external",
    status_code=status.HTTP_201_CREATED,
    summary="Create mapping for external bank account",
    responses={
        201: {"description": "External account mapping created successfully"},
        200: {"description": "Mapping already exists (returned existing)"},
        400: {"description": "Invalid IBAN or request"},
    },
)
async def create_external_account_mapping(
    request: ExternalAccountCreateRequest,
    factory: RepoFactory,
) -> ExternalAccountCreateResponse:
    """
    Create an account mapping for an external bank account.

    Use this for accounts at institutions that don't offer FinTS access.

    ## Account Types

    - **asset** (default): Bank accounts, stock portfolios, foreign banks.
      Transfers are tracked as internal transfers (Asset ↔ Asset).

    - **liability**: Credit cards, loans, mortgages.
      Payments are tracked as liability payments (reduces what you owe).

    ## Reconciliation

    If reconcile=true, existing transactions to this IBAN are retroactively
    updated. Currently only implemented for asset accounts.

    ## Examples

    - Stock portfolio: Create as **asset** → monthly transfers become internal
    - Credit card: Create as **liability** → payments reduce debt
    """
    command = CreateExternalAccountCommand.from_factory(factory)

    domain_account_type = (
        AccountType.LIABILITY
        if request.account_type == ExternalAccountType.LIABILITY
        else AccountType.ASSET
    )

    try:
        result = await command.execute(
            iban=request.iban,
            name=request.name,
            currency=request.currency,
            account_type=domain_account_type,
            reconcile=request.reconcile,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        raise

    logger.info(
        "External account mapping created: %s -> %s (reconciled %d transactions)",
        request.iban,
        request.name,
        result.transactions_reconciled,
    )

    return ExternalAccountCreateResponse.model_validate(result.model_dump())
