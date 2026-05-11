"""Banking DTOs. Data transfer objects for bank connection results."""

from swen.application.dtos.banking.connection_result import (
    AccountInfo,
    ConnectionResult,
)
from swen.application.dtos.banking.discovered_accounts_dto import (
    DiscoveredAccountDTO,
    DiscoveredAccountsCollectionDTO,
)

__all__ = [
    "AccountInfo",
    "ConnectionResult",
    "DiscoveredAccountDTO",
    "DiscoveredAccountsCollectionDTO",
]
