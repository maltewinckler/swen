"""Repository interfaces for banking domain."""

from swen.domain.banking.repositories.bank_account_repository import (
    BankAccountRepository,
)
from swen.domain.banking.repositories.bank_credential_repository import (
    BankCredentialRepository,
)
from swen.domain.banking.repositories.bank_transaction_repository import (
    BankTransactionRepository,
    StoredBankTransaction,
)

__all__ = [
    "BankAccountRepository",
    "BankCredentialRepository",
    "BankTransactionRepository",
    "StoredBankTransaction",
]
