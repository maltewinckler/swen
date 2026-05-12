"""Integration queries - read operations on sync status, imports, and mappings."""

from swen.application.integration.queries.bank_connection_details_query import (
    BankConnectionDetailsQuery,
)
from swen.application.integration.queries.list_account_mappings_query import (
    AccountMappingListResult,
    ListAccountMappingsQuery,
    MappingWithAccount,
)
from swen.application.integration.queries.list_imports_query import (
    ImportListResult,
    ImportStatistics,
    ListImportsQuery,
)
from swen.application.integration.queries.reconciliation_query import (
    ReconciliationQuery,
)
from swen.application.integration.queries.sync_recommendation_query import (
    SyncRecommendationQuery,
)
from swen.application.integration.queries.sync_status_query import (
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
    "ReconciliationQuery",
    "SyncRecommendationQuery",
    "SyncStatusQuery",
    "SyncStatusResult",
]
