"""Mappings router for bank account to ledger account mappings."""

import logging

from fastapi import APIRouter, HTTPException, status
from swen.application.commands.integration import CreateExternalAccountCommand
from swen.application.queries.integration import (
    ListAccountMappingsQuery,
)
from swen.domain.accounting.entities import AccountType
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.mappings import (
    ExternalAccountCreateRequest,
    ExternalAccountCreateResponse,
    ExternalAccountType,
    MappingListResponse,
    MappingResponse,
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
async def list_mappings(
    factory: RepoFactory,
) -> MappingListResponse:
    """
    List all bank account to ledger account mappings.

    These mappings connect imported bank accounts (identified by IBAN)
    to accounting accounts in your chart of accounts.

    Each mapping shows:
    - The bank account IBAN and name
    - The linked ledger account (for categorization)
    """
    query = ListAccountMappingsQuery.from_factory(factory)
    results = await query.get_all_with_accounts()

    mappings = [
        MappingResponse(
            id=r.mapping.id,
            iban=r.mapping.iban,
            account_name=r.mapping.account_name,
            accounting_account_id=r.mapping.accounting_account_id,
            accounting_account_name=r.account.name if r.account else None,
            accounting_account_number=r.account.account_number if r.account else None,
            created_at=r.mapping.created_at.isoformat()
            if r.mapping.created_at
            else None,
        )
        for r in results
    ]

    return MappingListResponse(
        mappings=mappings,
        count=len(mappings),
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
) -> MappingResponse:
    """
    Get a specific bank account mapping by IBAN.

    Use this to check which ledger account a bank account is mapped to.
    """
    query = ListAccountMappingsQuery.from_factory(factory)
    result = await query.get_mapping_with_account(iban)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No mapping found for IBAN: {iban}",
        )

    return MappingResponse(
        id=result.mapping.id,
        iban=result.mapping.iban,
        account_name=result.mapping.account_name,
        accounting_account_id=result.mapping.accounting_account_id,
        accounting_account_name=result.account.name if result.account else None,
        accounting_account_number=result.account.account_number
        if result.account
        else None,
        created_at=result.mapping.created_at.isoformat()
        if result.mapping.created_at
        else None,
    )

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
    - Credit card (Norwegian Bank): Create as **liability** → payments reduce debt
    """
    command = CreateExternalAccountCommand.from_factory(factory)

    # Convert API enum to domain enum
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
        # Let the global exception handler process domain exceptions
        raise

    mapping_response = MappingResponse(
        id=result.mapping.id,
        iban=result.mapping.iban,
        account_name=result.mapping.account_name,
        accounting_account_id=result.mapping.accounting_account_id,
        accounting_account_name=result.account.name,
        accounting_account_number=result.account.account_number,
        created_at=(
            result.mapping.created_at.isoformat() if result.mapping.created_at else None
        ),
    )

    logger.info(
        "External account mapping created: %s -> %s (reconciled %d transactions)",
        request.iban,
        request.name,
        result.transactions_reconciled,
    )

    return ExternalAccountCreateResponse(
        mapping=mapping_response,
        transactions_reconciled=result.transactions_reconciled,
        already_existed=result.already_existed,
    )
