"""Imports router for transaction import history."""

import logging
from typing import Annotated

from fastapi import APIRouter, Query

from swen.application.integration.queries import ListImportsQuery
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.integration.schemas.imported_transactions import (
    ImportedTransactionsListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


DaysFilter = Annotated[int, Query(ge=1, le=730, description="Days to look back")]
LimitFilter = Annotated[int, Query(ge=1, le=500, description="Maximum imports")]
FailedOnlyFilter = Annotated[bool, Query(description="Only show failed imports")]
IbanFilter = Annotated[str | None, Query(description="Filter by bank account IBAN")]


@router.get(
    "",
    summary="List import history",
    responses={
        200: {"description": "List of import records"},
    },
)
async def list_imports(
    factory: RepoFactory,
    days: DaysFilter = 30,
    limit: LimitFilter = 50,
    failed_only: FailedOnlyFilter = False,
    iban: IbanFilter = None,
) -> ImportedTransactionsListResponse:
    """
    List transaction import history.

    Shows the history of bank transaction imports, including:
    - Successfully imported transactions
    - Failed imports (with error messages)
    - Duplicate detections
    - Pending imports awaiting review

    **Use cases:**
    - Troubleshoot sync issues
    - Review failed imports
    - Audit import history
    """
    query = ListImportsQuery.from_factory(factory)
    result = await query.execute(
        days=days,
        limit=limit,
        failed_only=failed_only,
        iban_filter=iban,
    )

    return ImportedTransactionsListResponse.model_validate(result)
