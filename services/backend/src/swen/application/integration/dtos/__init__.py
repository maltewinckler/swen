"""Integration DTOs. Data transfer objects for sync, import, and mapping results."""

from swen.application.integration.dtos.account_mapping_dto import (
    AccountMappingDTO,
    AccountMappingListDTO,
)
from swen.application.integration.dtos.bank_connection_details_dto import (
    BankAccountDetailDTO,
    BankConnectionDetailsDTO,
)
from swen.application.integration.dtos.imported_transactions_dto import (
    ImportedTransactionDTO,
    ImportedTransactionsListDTO,
)
from swen.application.integration.dtos.reconciliation_dto import (
    AccountReconciliationDTO,
    ReconciliationResultDTO,
)

__all__ = [
    "AccountMappingDTO",
    "AccountMappingListDTO",
    "AccountReconciliationDTO",
    "BankAccountDetailDTO",
    "BankConnectionDetailsDTO",
    "ImportedTransactionDTO",
    "ImportedTransactionsListDTO",
    "ReconciliationResultDTO",
]
