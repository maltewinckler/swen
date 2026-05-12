"""Integration DTOs. Data transfer objects for sync and import results."""

from swen.application.integration.dtos.bank_connection_details_dto import (
    BankAccountDetailDTO,
    BankConnectionDetailsDTO,
)
from swen.application.integration.dtos.reconciliation_dto import (
    AccountReconciliationDTO,
    ReconciliationResultDTO,
)
from swen.application.integration.dtos.sync_recommendation_dto import (
    AccountSyncRecommendationDTO,
    SyncRecommendationResultDTO,
)
from swen.application.integration.dtos.transaction_import_result import (
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
