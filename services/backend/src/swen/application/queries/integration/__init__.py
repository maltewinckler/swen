"""Integration queries - read operations on sync status, imports, and mappings."""

from swen.application.queries.integration.bank_connection_details_query import (
    BankConnectionDetailsQuery,
)
from swen.application.queries.integration.list_account_mappings_query import (
    AccountMappingListResult,
    ListAccountMappingsQuery,
    MappingWithAccount,
)
from swen.application.queries.integration.list_imports_query import (
    ImportListResult,
    ImportStatistics,
    ListImportsQuery,
)
from swen.application.queries.integration.opening_balance_query import (
    OpeningBalanceQuery,
)
from swen.application.queries.integration.reconciliation_query import (
    ReconciliationQuery,
)
from swen.application.queries.integration.sync_recommendation_query import (
    SyncRecommendationQuery,
)
from swen.application.queries.integration.sync_status_query import (
    SyncStatusQuery,
    SyncStatusResult,
)

__all__ = [
    "AccountMappingListResult",
    "BankConnectionDetailsQuery",
    "ImportListResult",
    "ImportStatistics",
    "ListAccountMappingsQuery",
    "ListImportsQuery",
    "MappingWithAccount",
    "OpeningBalanceQuery",
    "ReconciliationQuery",
    "SyncRecommendationQuery",
    "SyncStatusQuery",
    "SyncStatusResult",
]
