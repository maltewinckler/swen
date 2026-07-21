"""Exports router for data export endpoints."""

import logging
from datetime import date
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from swen.application.analytics.queries import ExportDataQuery
from swen.application.analytics.queries.export_report_query import ExportReportQuery
from swen.domain.shared.time import utc_now
from swen.infrastructure.export import ExcelReportGenerator
from swen.presentation.api.analytics.schemas.exports import (
    AccountExportListResponse,
    FullExportResponse,
    TransactionExportListResponse,
)
from swen.presentation.api.dependencies import RepoFactory

logger = logging.getLogger(__name__)

router = APIRouter()

DaysFilter = Annotated[
    int,
    Query(ge=0, le=3650, description="Days to look back (0 = all time)"),
]
StatusFilter = Annotated[
    str | None,
    Query(description="Filter: 'all', 'posted', 'draft' (default: user preference)"),
]
IbanFilter = Annotated[
    str | None,
    Query(description="Filter by bank account IBAN"),
]
AccountTypeFilter = Annotated[
    str | None,
    Query(description="Filter by type: asset, liability, equity, income, expense"),
]
IncludeInactiveFilter = Annotated[
    bool,
    Query(description="Include inactive accounts"),
]

# Excel export parameters
StartDateParam = Annotated[
    date | None,
    Query(description="Start date (YYYY-MM-DD) for custom date range"),
]
EndDateParam = Annotated[
    date | None,
    Query(description="End date (YYYY-MM-DD) for custom date range"),
]
MonthParam = Annotated[
    str | None,
    Query(pattern=r"^\d{4}-\d{2}$", description="Specific month (YYYY-MM format)"),
]
IncludeDraftsParam = Annotated[
    bool,
    Query(description="Include draft (non-posted) transactions"),
]


@router.get(
    "/transactions",
    summary="Export transactions",
    responses={
        200: {"description": "Transaction export data"},
    },
)
async def export_transactions(
    factory: RepoFactory,
    days: DaysFilter = 0,
    status: StatusFilter = None,
    iban: IbanFilter = None,
) -> TransactionExportListResponse:
    """
    Export transactions for backup or analysis.

    **Parameters:**
    - **days**: Number of days to look back (0 = all transactions)
    - **status**: Filter by status - 'all', 'posted', 'draft'
    - **iban**: Filter by bank account IBAN

    **Use cases:**
    - Export recent transactions for spreadsheet analysis
    - Backup posted transactions
    - Export specific bank account's transactions
    """
    query = ExportDataQuery.from_factory(factory)
    transactions = await query.get_transactions(days=days, status=status, iban=iban)

    logger.info("Exported %d transactions", len(transactions))

    return TransactionExportListResponse(transactions=transactions)


@router.get(
    "/accounts",
    summary="Export accounts",
    responses={
        200: {"description": "Account export data"},
    },
)
async def export_accounts(
    factory: RepoFactory,
    account_type: AccountTypeFilter = None,
    include_inactive: IncludeInactiveFilter = False,
) -> AccountExportListResponse:
    """
    Export chart of accounts for backup or migration.

    **Parameters:**
    - **account_type**: Filter by type (asset, liability, equity, income, expense)
    - **include_inactive**: Include deactivated accounts (default: false)
    """
    query = ExportDataQuery.from_factory(factory)
    accounts = await query.get_accounts(
        account_type=account_type,
        include_inactive=include_inactive,
    )

    logger.info("Exported %d accounts", len(accounts))

    return AccountExportListResponse(accounts=accounts)


@router.get(
    "/full",
    summary="Full data export (backup)",
    responses={
        200: {"description": "Complete data export"},
    },
)
async def export_full(
    factory: RepoFactory,
    days: DaysFilter = 0,
) -> FullExportResponse:
    """
    Export all user data for backup.

    Includes:
    - All transactions (posted and draft)
    - All accounts (including inactive)
    - All bank account mappings

    **Parameters:**
    - **days**: Transaction history limit (0 = all time)

    **Use case:** Create a complete backup before data migration or cleanup.
    """
    query = ExportDataQuery.from_factory(factory)
    result = await query.execute_full_export(days=days)

    logger.info(
        "Full export: %d transactions, %d accounts, %d mappings",
        result.transaction_count,
        result.account_count,
        result.mapping_count,
    )

    return FullExportResponse.model_validate(result)


@router.get(
    "/report.xlsx",
    summary="Download Excel report",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "Excel file download",
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
        },
    },
)
async def export_excel_report(  # noqa: PLR0913
    factory: RepoFactory,
    start_date: StartDateParam = None,
    end_date: EndDateParam = None,
    days: DaysFilter = 0,
    month: MonthParam = None,
    include_drafts: IncludeDraftsParam = True,
) -> StreamingResponse:
    """
    Download a comprehensive Excel report.

    The report contains multiple sheets:
    - **Dashboard**: Summary metrics, net worth, month comparison
    - **Transactions**: Full transaction data with bank metadata
    - **Accounts**: Chart of accounts
    - **Mappings**: Bank account mappings

    **Date Range Options** (priority order):
    1. `start_date` + `end_date`: Custom date range
    2. `days`: Rolling window (last N days)
    3. `month`: Specific month (YYYY-MM)
    4. All time (if none provided)

    **Quick Access Examples:**
    - Last 30 days: `?days=30`
    - Last 90 days: `?days=90`
    - Specific month: `?month=2024-12`
    - Custom range: `?start_date=2024-01-01&end_date=2024-06-30`
    """
    query = ExportReportQuery.from_factory(factory)

    # Execute query with date parameters
    # days=0 means "not specified" (use other params or all time)
    data = await query.execute(
        start_date=start_date,
        end_date=end_date,
        days=days if days > 0 else None,
        month=month,
        include_drafts=include_drafts,
    )

    # Generate Excel file
    generator = ExcelReportGenerator()
    excel_bytes = generator.generate(data)

    # Create filename with timestamp
    timestamp = utc_now().strftime("%Y-%m-%d")
    filename = f"swen_report_{timestamp}.xlsx"

    logger.info(
        "Excel report generated: %d transactions, %d accounts",
        data.transaction_count,
        data.account_count,
    )

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
