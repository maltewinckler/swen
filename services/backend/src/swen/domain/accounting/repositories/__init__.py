"""Repository interfaces for the accounting domain."""

from swen.domain.accounting.repositories.account_repository import AccountRepository
from swen.domain.accounting.repositories.transaction_repository import (
    TransactionRepository,
)

__all__ = ["AccountRepository", "TransactionRepository"]
