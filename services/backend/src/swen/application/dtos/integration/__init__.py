"""Integration DTOs. Data transfer objects for sync and import results."""

from swen.application.dtos.integration.bank_connection_details_dto import (
    BankAccountDetailDTO,
    BankConnectionDetailsDTO,
)
from swen.application.dtos.integration.reconciliation_dto import (
    AccountReconciliationDTO,
    ReconciliationResultDTO,
)
from swen.application.dtos.integration.sync_recommendation_dto import (
    AccountSyncRecommendationDTO,
    SyncRecommendationResultDTO,
)
from swen.application.dtos.integration.transaction_import_result import (
    TransactionImportResult,
)

__all__ = [
    "AccountReconciliationDTO",
    "AccountSyncRecommendationDTO",
    "BankAccountDetailDTO",
    "BankConnectionDetailsDTO",
    "ReconciliationResultDTO",
    "SyncRecommendationResultDTO",
    "TransactionImportResult",
]
