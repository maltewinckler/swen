"""Repository factory protocol for application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from swen.application.ports.analytics import AnalyticsReadPort
from swen.application.ports.unit_of_work import UnitOfWork
from swen.domain.accounting.repositories import (
    AccountRepository,
    TransactionRepository,
)
from swen.domain.banking.ports import BankConnectionPort
from swen.domain.banking.repositories import (
    BankAccountRepository,
    BankCredentialRepository,
    BankInfoRepository,
    BankTransactionRepository,
)
from swen.domain.integration.repositories import (
    AccountMappingRepository,
    TransactionImportRepository,
)
from swen.domain.settings import UserSettingsRepository
from swen.infrastructure.banking.geldstrom_api.config_repository import (
    GeldstromApiConfigRepository,
)
from swen.infrastructure.banking.local_fints.repositories.config_repository import (
    FinTSConfigRepository,
)
from swen.infrastructure.banking.local_fints.repositories.endpoint_repository import (
    FinTSEndpointRepository,
)
from swen_identity.domain.repositories import UserRepository

if TYPE_CHECKING:
    from swen.domain.shared.current_user import CurrentUser


class RepositoryFactory(Protocol):
    """Protocol for creating user-scoped repositories."""

    @property
    def current_user(self) -> CurrentUser:
        """Get the current user for repository scoping."""
        ...

    @property
    def session(self) -> Any:
        """Get the database session (legacy — prefer unit_of_work())."""
        ...

    def unit_of_work(self) -> UnitOfWork:
        """Get a unit-of-work scoped to the current request session."""
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

    # Strictly speaking, this is a DDD violation because FinTS should be
    # considered as infrastructure. But since it is so deeply integrated,
    # we will ignore Fints and Geldstrom concerns for now and allow them
    # in the application layer.
    def fints_config_repository(self) -> FinTSConfigRepository:
        """Get FinTS configuration repository (system-wide)."""
        ...

    def geldstrom_api_config_repository(self) -> GeldstromApiConfigRepository:
        """Get Geldstrom API configuration repository (system-wide)."""
        ...

    def bank_info_repository(self) -> BankInfoRepository:
        """Get bank information repository (system-wide)."""
        ...

    def fints_endpoint_repository(self) -> FinTSEndpointRepository:
        """Get FinTS endpoint repository (system-wide)."""
        ...

    def bank_connection_port(self) -> BankConnectionPort:
        """Get the bank connection port (dispatcher) for outbound bank I/O."""
        ...
