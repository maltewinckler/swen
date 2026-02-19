"""SQLAlchemy repository factory for creating user-scoped repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from swen.infrastructure.persistence.sqlalchemy.adapters.analytics import (
    SqlAlchemyAnalyticsReadAdapter,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    BankAccountRepositorySQLAlchemy,
    BankCredentialRepositorySQLAlchemy,
    BankTransactionRepositorySQLAlchemy,
    FinTSConfigRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
    CounterAccountRuleRepositorySQLAlchemy,
    TransactionImportRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.security import (
    StoredBankCredentialsRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.settings import (
    UserSettingsRepositorySQLAlchemy,
)
from swen.infrastructure.security.encryption_service_fernet import (
    FernetEncryptionService,
)
from swen_identity.infrastructure.persistence.sqlalchemy import (
    UserRepositorySQLAlchemy,
)

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser


class SQLAlchemyRepositoryFactory:
    """SQLAlchemy implementation of the RepositoryFactory Protocol."""

    def __init__(
        self,
        session: AsyncSession,
        current_user: CurrentUser,
        encryption_key: bytes,
    ):
        self._session = session
        self._current_user = current_user
        self._encryption_key = encryption_key

        # Cached instances (created on demand)
        self._account_repo: AccountRepositorySQLAlchemy | None = None
        self._transaction_repo: TransactionRepositorySQLAlchemy | None = None
        self._mapping_repo: AccountMappingRepositorySQLAlchemy | None = None
        self._import_repo: TransactionImportRepositorySQLAlchemy | None = None
        self._rule_repo: CounterAccountRuleRepositorySQLAlchemy | None = None
        self._credential_repo: BankCredentialRepositorySQLAlchemy | None = None
        self._bank_account_repo: BankAccountRepositorySQLAlchemy | None = None
        self._bank_transaction_repo: BankTransactionRepositorySQLAlchemy | None = None
        self._analytics_read_adapter: SqlAlchemyAnalyticsReadAdapter | None = None
        self._settings_repo: UserSettingsRepositorySQLAlchemy | None = None
        self._fints_config_repo: FinTSConfigRepositorySQLAlchemy | None = None

    @property
    def current_user(self) -> CurrentUser:
        return self._current_user

    @property
    def session(self) -> AsyncSession:
        return self._session

    def account_repository(self) -> AccountRepositorySQLAlchemy:
        if self._account_repo is None:
            self._account_repo = AccountRepositorySQLAlchemy(
                self._session,
                self._current_user,
            )
        return self._account_repo

    def transaction_repository(self) -> TransactionRepositorySQLAlchemy:
        if self._transaction_repo is None:
            self._transaction_repo = TransactionRepositorySQLAlchemy(
                self._session,
                self.account_repository(),
                self._current_user,
            )
        return self._transaction_repo

    def account_mapping_repository(self) -> AccountMappingRepositorySQLAlchemy:
        if self._mapping_repo is None:
            self._mapping_repo = AccountMappingRepositorySQLAlchemy(
                self._session,
                self._current_user,
            )
        return self._mapping_repo

    def import_repository(self) -> TransactionImportRepositorySQLAlchemy:
        if self._import_repo is None:
            self._import_repo = TransactionImportRepositorySQLAlchemy(
                self._session,
                self._current_user,
            )
        return self._import_repo

    def counter_account_rule_repository(self) -> CounterAccountRuleRepositorySQLAlchemy:
        if self._rule_repo is None:
            self._rule_repo = CounterAccountRuleRepositorySQLAlchemy(
                self._session,
                self._current_user,
            )
        return self._rule_repo

    def credential_repository(self) -> BankCredentialRepositorySQLAlchemy:
        if self._credential_repo is None:
            encryption_service = FernetEncryptionService(
                encryption_key=self._encryption_key,
            )
            stored_repo = StoredBankCredentialsRepositorySQLAlchemy(
                self._session,
                self._current_user,
            )
            self._credential_repo = BankCredentialRepositorySQLAlchemy(
                stored_repo,
                encryption_service,
                self._current_user,
            )
        return self._credential_repo

    def bank_account_repository(self) -> BankAccountRepositorySQLAlchemy:
        if self._bank_account_repo is None:
            self._bank_account_repo = BankAccountRepositorySQLAlchemy(
                self._session,
                self._current_user,
            )
        return self._bank_account_repo

    def bank_transaction_repository(self) -> BankTransactionRepositorySQLAlchemy:
        if self._bank_transaction_repo is None:
            self._bank_transaction_repo = BankTransactionRepositorySQLAlchemy(
                self._session,
                self._current_user,
            )
        return self._bank_transaction_repo

    def analytics_read_port(self) -> SqlAlchemyAnalyticsReadAdapter:
        if self._analytics_read_adapter is None:
            self._analytics_read_adapter = SqlAlchemyAnalyticsReadAdapter(
                self._session,
                self._current_user,
            )
        return self._analytics_read_adapter

    def user_repository(self) -> UserRepositorySQLAlchemy:
        return UserRepositorySQLAlchemy(self._session)

    def user_settings_repository(self) -> UserSettingsRepositorySQLAlchemy:
        if self._settings_repo is None:
            self._settings_repo = UserSettingsRepositorySQLAlchemy(
                self._session,
                self._current_user,
            )
        return self._settings_repo

    def fints_config_repository(self) -> FinTSConfigRepositorySQLAlchemy:
        """Get FinTS configuration repository (system-wide, not user-scoped)."""
        if self._fints_config_repo is None:
            encryption_service = FernetEncryptionService(
                encryption_key=self._encryption_key,
            )
            self._fints_config_repo = FinTSConfigRepositorySQLAlchemy(
                self._session,
                encryption_service,
            )
        return self._fints_config_repo
