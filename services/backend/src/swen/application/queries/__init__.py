"""Query layer. Read-only operations for retrieving data."""

from swen.application.dtos.accounting import (
    JournalEntryDTO,
    TransactionDetailDTO,
    TransactionListItemDTO,
    TransactionListResultDTO,
)
from swen.application.dtos.export_dto import (
    AccountExportDTO,
    ExportResult,
    MappingExportDTO,
    TransactionExportDTO,
)
from swen.application.dtos.integration import (
    AccountSyncRecommendationDTO,
    SyncRecommendationResultDTO,
)
from swen.application.queries.accounting import (
    AccountBalanceQuery,
    AccountListResult,
    AccountStatsQuery,
    ListAccountsQuery,
    ListTransactionsQuery,
    TransactionListResult,
)
from swen.application.queries.analytics import (
    BalanceHistoryQuery,
    CategoryComparison,
    IncomeBreakdownQuery,
    IncomeOverTimeQuery,
    MonthComparisonQuery,
    MonthComparisonResult,
    NetIncomeOverTimeQuery,
    NetWorthQuery,
    SankeyData,
    SankeyLink,
    SankeyNode,
    SankeyQuery,
    SavingsRateQuery,
    SingleAccountSpendingQuery,
    SpendingBreakdownQuery,
    SpendingOverTimeQuery,
    TopExpenseItem,
    TopExpensesQuery,
    TopExpensesResult,
)
from swen.application.queries.banking import (
    CredentialInfo,
    CredentialListResult,
    ListCredentialsQuery,
    QueryTanMethodsQuery,
    TANMethodInfo,
    TANMethodsResult,
)
from swen.application.queries.dashboard_summary_query import (
    DashboardSummary,
    DashboardSummaryQuery,
)
from swen.application.queries.export_data_query import ExportDataQuery
from swen.application.queries.export_report_query import ExportReportQuery
from swen.application.queries.integration import (
    AccountMappingListResult,
    ImportListResult,
    ImportStatistics,
    ListAccountMappingsQuery,
    ListImportsQuery,
    MappingWithAccount,
    ReconciliationQuery,
    SyncRecommendationQuery,
    SyncStatusQuery,
    SyncStatusResult,
)
from swen.application.queries.onboarding import (
    OnboardingStatus,
    OnboardingStatusQuery,
)
from swen.application.queries.settings import GetUserSettingsQuery
from swen.application.queries.system import (
    DatabaseIntegrityQuery,
    IntegrityCheckResult,
    IntegrityIssue,
    IssueSeverity,
    IssueType,
)
from swen.application.queries.user import GetCurrentUserQuery

__all__ = [
    # Accounting
    "AccountBalanceQuery",
    "AccountListResult",
    "AccountStatsQuery",
    "ListAccountsQuery",
    "ListTransactionsQuery",
    "TransactionListResult",
    # Analytics
    "BalanceHistoryQuery",
    "CategoryComparison",
    "IncomeBreakdownQuery",
    "IncomeOverTimeQuery",
    "MonthComparisonQuery",
    "MonthComparisonResult",
    "NetIncomeOverTimeQuery",
    "NetWorthQuery",
    "SankeyData",
    "SankeyLink",
    "SankeyNode",
    "SankeyQuery",
    "SavingsRateQuery",
    "SingleAccountSpendingQuery",
    "SpendingBreakdownQuery",
    "SpendingOverTimeQuery",
    "TopExpenseItem",
    "TopExpensesQuery",
    "TopExpensesResult",
    # Banking
    "CredentialInfo",
    "CredentialListResult",
    "ListCredentialsQuery",
    "QueryTanMethodsQuery",
    "TANMethodInfo",
    "TANMethodsResult",
    # Integration
    "AccountMappingListResult",
    "ImportListResult",
    "ImportStatistics",
    "ListAccountMappingsQuery",
    "ListImportsQuery",
    "MappingWithAccount",
    "ReconciliationQuery",
    "SyncRecommendationQuery",
    "SyncStatusQuery",
    "SyncStatusResult",
    # Onboarding
    "OnboardingStatus",
    "OnboardingStatusQuery",
    # User
    "GetCurrentUserQuery",
    # Settings
    "GetUserSettingsQuery",
    # System
    "DatabaseIntegrityQuery",
    "IntegrityCheckResult",
    "IntegrityIssue",
    "IssueSeverity",
    "IssueType",
    # Cross-domain
    "DashboardSummary",
    "DashboardSummaryQuery",
    "ExportDataQuery",
    "ExportReportQuery",
    # DTOs
    "AccountExportDTO",
    "AccountSyncRecommendationDTO",
    "ExportResult",
    "JournalEntryDTO",
    "MappingExportDTO",
    "SyncRecommendationResultDTO",
    "TransactionDetailDTO",
    "TransactionExportDTO",
    "TransactionListItemDTO",
    "TransactionListResultDTO",
]
