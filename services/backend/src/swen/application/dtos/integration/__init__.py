"""Integration DTOs. Data transfer objects for sync and import results."""

from swen.application.dtos.integration.bank_connection_details_dto import (
    BankAccountDetailDTO,
    BankConnectionDetailsDTO,
)
from swen.application.dtos.integration.batch_sync_result import (
    AccountSyncStats,
    BatchSyncResult,
    BatchSyncResultBuilder,
    OpeningBalanceInfo,
)
from swen.application.dtos.integration.reconciliation_dto import (
    AccountReconciliationDTO,
    ReconciliationResultDTO,
)
from swen.application.dtos.integration.sync_period import (
    SyncPeriod,
)
from swen.application.dtos.integration.sync_progress import (
    AccountSyncCompletedEvent,
    AccountSyncFailedEvent,
    AccountSyncFetchedEvent,
    AccountSyncStartedEvent,
    BatchSyncCompletedEvent,
    BatchSyncFailedEvent,
    BatchSyncStartedEvent,
    ClassificationCompletedEvent,
    ClassificationProgressEvent,
    ClassificationStartedEvent,
    ErrorCode,
    SyncEventType,
    SyncProgressEvent,
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
    "AccountReconciliationDTO",
    "AccountSyncCompletedEvent",
    "AccountSyncFailedEvent",
    "AccountSyncFetchedEvent",
    "AccountSyncStartedEvent",
    "AccountSyncRecommendationDTO",
    "AccountSyncStats",
    "BankAccountDetailDTO",
    "BankConnectionDetailsDTO",
    "BatchSyncCompletedEvent",
    "BatchSyncFailedEvent",
    "BatchSyncResult",
    "BatchSyncResultBuilder",
    "BatchSyncStartedEvent",
    "ClassificationCompletedEvent",
    "ClassificationProgressEvent",
    "ClassificationStartedEvent",
    "ErrorCode",
    "OpeningBalanceInfo",
    "ReconciliationResultDTO",
    "SyncEventType",
    "SyncPeriod",
    "SyncProgressEvent",
    "SyncRecommendationResultDTO",
    "SyncResult",
    "TransactionClassifiedEvent",
]
