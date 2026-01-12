"""SQLAlchemy repository factory for creating user-scoped repositories."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from swen.infrastructure.integration.ai import OllamaCounterAccountProvider
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
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
    CounterAccountRuleRepositorySQLAlchemy,
    TransactionImportRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.security import (
    StoredBankCredentialsRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.user import (
    UserRepositorySQLAlchemy,
)
from swen.infrastructure.security.encryption_service_fernet import (
    FernetEncryptionService,
)
from swen_config.settings import get_settings

if TYPE_CHECKING:
    from swen.application.context import UserContext
    from swen.domain.integration.services import AICounterAccountProvider

logger = logging.getLogger(__name__)


class SQLAlchemyRepositoryFactory:
    """SQLAlchemy implementation of the RepositoryFactory Protocol."""

    def __init__(
        self,
        session: AsyncSession,
        user_context: UserContext,
        encryption_key: bytes,
    ):
        self._session = session
        self._user_context = user_context
        self._encryption_key = encryption_key

        # Cached instances (created on demand)
        self._account_repo: AccountRepositorySQLAlchemy | None = None
        self._transaction_repo: TransactionRepositorySQLAlchemy | None = None
        self._mapping_repo: AccountMappingRepositorySQLAlchemy | None = None
        self._import_repo: TransactionImportRepositorySQLAlchemy | None = None
        self._rule_repo: CounterAccountRuleRepositorySQLAlchemy | None = None
        self._credential_repo: BankCredentialRepositorySQLAlchemy | None = None
        self._analytics_read_adapter: SqlAlchemyAnalyticsReadAdapter | None = None

    @property
    def user_context(self) -> UserContext:
        return self._user_context

    @property
    def session(self) -> AsyncSession:
        return self._session

    def account_repository(self) -> AccountRepositorySQLAlchemy:
        if self._account_repo is None:
            self._account_repo = AccountRepositorySQLAlchemy(
                self._session,
                self._user_context,
            )
        return self._account_repo

    def transaction_repository(self) -> TransactionRepositorySQLAlchemy:
        if self._transaction_repo is None:
            self._transaction_repo = TransactionRepositorySQLAlchemy(
                self._session,
                self.account_repository(),
                self._user_context,
            )
        return self._transaction_repo

    def account_mapping_repository(self) -> AccountMappingRepositorySQLAlchemy:
        if self._mapping_repo is None:
            self._mapping_repo = AccountMappingRepositorySQLAlchemy(
                self._session,
                self._user_context,
            )
        return self._mapping_repo

    def import_repository(self) -> TransactionImportRepositorySQLAlchemy:
        if self._import_repo is None:
            self._import_repo = TransactionImportRepositorySQLAlchemy(
                self._session,
                self._user_context,
            )
        return self._import_repo

    def counter_account_rule_repository(self) -> CounterAccountRuleRepositorySQLAlchemy:
        if self._rule_repo is None:
            self._rule_repo = CounterAccountRuleRepositorySQLAlchemy(
                self._session,
                self._user_context,
            )
        return self._rule_repo

    def credential_repository(self) -> BankCredentialRepositorySQLAlchemy:
        if self._credential_repo is None:
            encryption_service = FernetEncryptionService(
                encryption_key=self._encryption_key,
            )
            stored_repo = StoredBankCredentialsRepositorySQLAlchemy(
                self._session,
                self._user_context,
            )
            self._credential_repo = BankCredentialRepositorySQLAlchemy(
                stored_repo,
                encryption_service,
                self._user_context,
            )
        return self._credential_repo

    def bank_account_repository(self) -> BankAccountRepositorySQLAlchemy:
        return BankAccountRepositorySQLAlchemy(self._session, self._user_context)

    def bank_transaction_repository(self) -> BankTransactionRepositorySQLAlchemy:
        return BankTransactionRepositorySQLAlchemy(self._session, self._user_context)

    def analytics_read_port(self) -> SqlAlchemyAnalyticsReadAdapter:
        if self._analytics_read_adapter is None:
            self._analytics_read_adapter = SqlAlchemyAnalyticsReadAdapter(
                self._session,
                self._user_context,
            )
        return self._analytics_read_adapter

    def user_repository(self) -> UserRepositorySQLAlchemy:
        return UserRepositorySQLAlchemy(self._session)


@lru_cache(maxsize=1)
def create_ai_provider_from_settings() -> Optional[AICounterAccountProvider]:
    """Create an AI provider from application settings (cached)."""
    settings = get_settings()

    ai_enabled: bool = settings.ai_enabled
    ai_provider_name: str = settings.ai_provider

    if not ai_enabled:
        logger.debug("AI counter-account resolution is disabled")
        return None

    if ai_provider_name == "ollama":
        model: str = settings.ai_ollama_model
        base_url: str = settings.ollama_base_url
        min_confidence: float = settings.ai_min_confidence
        timeout: float = settings.ai_ollama_timeout

        logger.info(
            "Creating Ollama AI provider (model: %s, url: %s)",
            model,
            base_url,
        )

        return OllamaCounterAccountProvider(
            model=model,
            base_url=base_url,
            min_confidence=min_confidence,
            timeout=timeout,
        )

    logger.warning("Unknown AI provider: %s", ai_provider_name)
    return None
