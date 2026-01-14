"""Repository factory protocol for application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from swen.application.ports.analytics import AnalyticsReadPort
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.banking.repositories import (
    BankAccountRepository,
    BankCredentialRepository,
    BankTransactionRepository,
)
from swen.domain.integration.repositories import (
    AccountMappingRepository,
    CounterAccountRuleRepository,
    TransactionImportRepository,
)
from swen.domain.settings import UserSettingsRepository
from swen_identity.domain.user.repositories import UserRepository

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser


class RepositoryFactory(Protocol):
    """Protocol for creating user-scoped repositories."""

    @property
    def current_user(self) -> CurrentUser:
        """Get the current user for repository scoping."""
        ...

    @property
    def session(self) -> Any:
        """Get the database session for transaction management.

        The type is intentionally `Any` to avoid coupling the
        application layer to specific database implementations.
        Use this for commit/rollback at the presentation layer.
        """
        ...

    def account_repository(self) -> AccountRepository:
        """Get account repository."""
        ...

    def transaction_repository(self) -> TransactionRepository:
        """Get transaction repository."""
        ...

    def account_mapping_repository(self) -> AccountMappingRepository:
        """Get account mapping repository."""
        ...

    def import_repository(self) -> TransactionImportRepository:
        """Get transaction import repository."""
        ...

    def counter_account_rule_repository(self) -> CounterAccountRuleRepository:
        """Get counter-account rule repository."""
        ...

    def credential_repository(self) -> BankCredentialRepository:
        """Get bank credential repository."""
        ...

    def bank_account_repository(self) -> BankAccountRepository:
        """Get bank account repository."""
        ...

    def bank_transaction_repository(self) -> BankTransactionRepository:
        """Get bank transaction repository."""
        ...

    def analytics_read_port(self) -> AnalyticsReadPort:
        """Get analytics read port."""
        ...

    def user_repository(self) -> UserRepository:
        """Get user repository."""
        ...

    def user_settings_repository(self) -> UserSettingsRepository:
        """Get user settings repository."""
        ...
