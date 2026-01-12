"""Pydantic schemas for API request/response models."""

from swen.presentation.api.schemas.accounts import (
    AccountCreateRequest,
    AccountListResponse,
    AccountResponse,
    AccountStatsResponse,
    AccountUpdateRequest,
    AccountWithBalanceResponse,
    BankAccountListResponse,
    BankAccountRenameRequest,
    BankAccountResponse,
)
from swen.presentation.api.schemas.analytics import (
    BreakdownItemResponse,
    CategoryDataResponse,
    CategoryTimeSeriesResponse,
    TimeSeriesDataPointResponse,
    TimeSeriesResponse,
)
from swen.presentation.api.schemas.analytics import (
    SpendingBreakdownResponse as AnalyticsSpendingBreakdownResponse,
)
from swen.presentation.api.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from swen.presentation.api.schemas.common import ErrorResponse, HealthResponse
from swen.presentation.api.schemas.credentials import (
    AccountImportInfo,
    BankLookupResponse,
    ConnectionTestResponse,
    CredentialCreateRequest,
    CredentialCreateResponse,
    CredentialListResponse,
    CredentialResponse,
    SetupBankResponse,
)
from swen.presentation.api.schemas.dashboard import (
    AccountBalanceResponse,
    BalancesResponse,
    CategorySpendingResponse,
    DashboardSummaryResponse,
    RecentTransactionResponse,
    SpendingBreakdownResponse,
)
from swen.presentation.api.schemas.mappings import (
    ExternalAccountCreateRequest,
    ExternalAccountCreateResponse,
    MappingListResponse,
    MappingResponse,
)
from swen.presentation.api.schemas.sync import (
    AccountSyncStatsResponse,
    OpeningBalanceResponse,
    SyncRunRequest,
    SyncRunResponse,
    SyncStatusResponse,
)
from swen.presentation.api.schemas.transactions import (
    JournalEntryResponse,
    TransactionListItemResponse,
    TransactionListResponse,
    TransactionResponse,
)

__all__ = [
    # Auth schemas
    "RegisterRequest",
    "LoginRequest",
    "RefreshRequest",
    "ChangePasswordRequest",
    "AuthResponse",
    "TokenResponse",
    "UserResponse",
    # Common schemas
    "ErrorResponse",
    "HealthResponse",
    # Account schemas
    "AccountResponse",
    "AccountStatsResponse",
    "AccountWithBalanceResponse",
    "AccountCreateRequest",
    "AccountUpdateRequest",
    "AccountListResponse",
    "BankAccountResponse",
    "BankAccountListResponse",
    "BankAccountRenameRequest",
    # Analytics schemas
    "TimeSeriesDataPointResponse",
    "CategoryDataResponse",
    "TimeSeriesResponse",
    "CategoryTimeSeriesResponse",
    "BreakdownItemResponse",
    "AnalyticsSpendingBreakdownResponse",
    # Credential schemas
    "CredentialResponse",
    "CredentialListResponse",
    "CredentialCreateRequest",
    "CredentialCreateResponse",
    "BankLookupResponse",
    "ConnectionTestResponse",
    "AccountImportInfo",
    "SetupBankResponse",
    # Sync schemas
    "SyncRunRequest",
    "SyncRunResponse",
    "AccountSyncStatsResponse",
    "OpeningBalanceResponse",
    "SyncStatusResponse",
    # Transaction schemas
    "JournalEntryResponse",
    "TransactionResponse",
    "TransactionListItemResponse",
    "TransactionListResponse",
    # Dashboard schemas
    "AccountBalanceResponse",
    "CategorySpendingResponse",
    "RecentTransactionResponse",
    "DashboardSummaryResponse",
    "SpendingBreakdownResponse",
    "BalancesResponse",
    # Mapping schemas
    "MappingResponse",
    "MappingListResponse",
    "ExternalAccountCreateRequest",
    "ExternalAccountCreateResponse",
]
