"""Integration DTOs. Data transfer objects for sync and import results."""

from swen.application.dtos.integration.bank_connection_details_dto import (
    BankAccountDetailDTO,
    BankConnectionDetailsDTO,
)
from swen.application.dtos.integration.batch_sync_result import (
    AccountSyncStats,
    BatchSyncResult,
    OpeningBalanceInfo,
)
from swen.application.dtos.integration.reconciliation_dto import (
    AccountReconciliationDTO,
    ReconciliationResultDTO,
)
from swen.application.dtos.integration.sync_progress import (
    AccountClassifyingEvent,
    AccountCompletedEvent,
    AccountFailedEvent,
    AccountFetchedEvent,
    AccountStartedEvent,
    SyncCompletedEvent,
    SyncEventType,
    SyncFailedEvent,
    SyncProgressEvent,
    SyncStartedEvent,
    TransactionClassifiedEvent,
)
from swen.application.dtos.integration.sync_recommendation_dto import (
    AccountSyncRecommendationDTO,
    SyncRecommendationResultDTO,
)
from swen.application.dtos.integration.sync_result import (
    SyncResult,
)

__all__ = [
    "AccountClassifyingEvent",
    "AccountCompletedEvent",
    "AccountFailedEvent",
    "AccountFetchedEvent",
    "AccountReconciliationDTO",
    "AccountStartedEvent",
    "AccountSyncRecommendationDTO",
    "AccountSyncStats",
    "BankAccountDetailDTO",
    "BankConnectionDetailsDTO",
    "BatchSyncResult",
    "OpeningBalanceInfo",
    "ReconciliationResultDTO",
    "SyncCompletedEvent",
    "SyncEventType",
    "SyncFailedEvent",
    "SyncProgressEvent",
    "SyncRecommendationResultDTO",
    "SyncResult",
    "SyncStartedEvent",
    "TransactionClassifiedEvent",
]
