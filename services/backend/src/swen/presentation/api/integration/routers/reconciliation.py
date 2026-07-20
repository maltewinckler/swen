"""Bank Account <-> Accounting Account reconciliation API router."""

import logging

from fastapi import APIRouter, HTTPException, status

from swen.application.integration.queries import (
    BankConnectionDetailsQuery,
    ReconciliationQuery,
)
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.integration.schemas.reconciliation import (
    BankConnectionDetailsResponse,
    ReconciliationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    summary="Reconcile bank balances with bookkeeping",
    responses={
        200: {"description": "Reconciliation results"},
    },
)
async def get_reconciliation(factory: RepoFactory) -> ReconciliationResponse:
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

    return ReconciliationResponse.model_validate(result)


@router.get(
    "/{blz}",
    summary="Get bank connection details with accounts",
    responses={
        200: {"description": "Bank connection details with all accounts"},
        404: {"description": "No accounts found for this bank connection"},
    },
)
async def get_bank_connection_details(
    blz: str,
    factory: RepoFactory,
) -> BankConnectionDetailsResponse:
    """
    Get details for a bank connection including all accounts and reconciliation.

    Returns all bank accounts under this connection with:
    - Bank-reported balance (from last sync)
    - Bookkeeping balance (calculated from transactions)
    - Reconciliation status (whether they match)

    This is useful for seeing the health of a specific bank connection
    and identifying any discrepancies.
    """
    # Validate BLZ format
    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )

    query = BankConnectionDetailsQuery.from_factory(factory)
    result = await query.execute(blz)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No accounts found for bank connection {blz}",
        )

    return BankConnectionDetailsResponse.model_validate(result)
