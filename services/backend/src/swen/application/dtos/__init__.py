"""Data Transfer Objects for presentation layer.

DTOs decouple the presentation layer from domain models,
providing stable interfaces for API endpoints and UI components.

DTOs are organized by domain:
- accounting: Account and transaction DTOs
- analytics: Chart and reporting DTOs
- banking: Bank connection result DTOs
- integration: Sync and import DTOs

Cross-domain DTOs (export) are at the root level.
"""

# Accounting DTOs
from swen.application.dtos.accounting import (
    AccountBalanceDTO,
    AccountStatsResult,
    AccountSummaryDTO,
    BankAccountDTO,
    ChartOfAccountsDTO,
    JournalEntryDTO,
    TransactionDetailDTO,
    TransactionListItemDTO,
    TransactionListResultDTO,
)

# Analytics DTOs
from swen.application.dtos.analytics import (
    BreakdownItem,
    CategoryTimeSeriesDataPoint,
    CategoryTimeSeriesResult,
    IncomeBreakdownResult,
    SpendingBreakdownResult,
    TimeSeriesDataPoint,
    TimeSeriesResult,
)

# Banking DTOs
from swen.application.dtos.banking import (
    AccountInfo,
    ConnectionResult,
)

# Cross-domain DTOs (at root level)
from swen.application.dtos.export_dto import (
    AccountExportDTO,
    ExportResult,
    MappingExportDTO,
    TransactionExportDTO,
)

# Integration DTOs
from swen.application.dtos.integration import (
    AccountSyncRecommendationDTO,
    AccountSyncStats,
    BatchSyncResult,
    OpeningBalanceInfo,
    SyncRecommendationResultDTO,
    SyncResult,
)

__all__ = [
    # Accounting
    "AccountBalanceDTO",
    "AccountStatsResult",
    "AccountSummaryDTO",
    "BankAccountDTO",
    "ChartOfAccountsDTO",
    "JournalEntryDTO",
    "TransactionDetailDTO",
    "TransactionListItemDTO",
    "TransactionListResultDTO",
    # Analytics
    "BreakdownItem",
    "CategoryTimeSeriesDataPoint",
    "CategoryTimeSeriesResult",
    "IncomeBreakdownResult",
    "SpendingBreakdownResult",
    "TimeSeriesDataPoint",
    "TimeSeriesResult",
    # Banking
    "AccountInfo",
    "ConnectionResult",
    # Integration
    "AccountSyncRecommendationDTO",
    "AccountSyncStats",
    "BatchSyncResult",
    "OpeningBalanceInfo",
    "SyncRecommendationResultDTO",
    "SyncResult",
    # Cross-domain
    "AccountExportDTO",
    "ExportResult",
    "MappingExportDTO",
    "TransactionExportDTO",
]
