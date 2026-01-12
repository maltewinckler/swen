"""SQLAlchemy repository implementations organized by bounded context."""

# Banking domain repositories
# Accounting domain repositories
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    BankAccountRepositorySQLAlchemy,
    BankTransactionRepositorySQLAlchemy,
)

# Repository Factory
from swen.infrastructure.persistence.sqlalchemy.repositories.factory import (
    SQLAlchemyRepositoryFactory,
)

# Integration domain repositories
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
    CounterAccountRuleRepositorySQLAlchemy,
    TransactionImportRepositorySQLAlchemy,
)

__all__ = [
    # Factory (recommended for creating repositories)
    "SQLAlchemyRepositoryFactory",
    # Banking
    "BankAccountRepositorySQLAlchemy",
    "BankTransactionRepositorySQLAlchemy",
    # Accounting
    "AccountRepositorySQLAlchemy",
    "TransactionRepositorySQLAlchemy",
    # Integration
    "AccountMappingRepositorySQLAlchemy",
    "TransactionImportRepositorySQLAlchemy",
    "CounterAccountRuleRepositorySQLAlchemy",
]
