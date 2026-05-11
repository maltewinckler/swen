"""Banking DTOs. Data transfer objects for bank connection results."""

from swen.application.dtos.banking.connection_result import (
    AccountInfo,
    ConnectionResult,
)
from swen.application.dtos.banking.discovered_accounts_dto import (
    BankDiscoveryResultDTO,
    DiscoveredAccountDTO,
)
from swen.application.dtos.banking.setup_banks_dto import (
    BankAccountToImportDTO,
    ImportedBankAccountDTO,
    SetupBankRequestDTO,
    SetupBankResponseDTO,
)

__all__ = [
    "AccountInfo",
    "ConnectionResult",
    "DiscoveredAccountDTO",
    "BankDiscoveryResultDTO",
    "BankAccountToImportDTO",
    "SetupBankRequestDTO",
    "SetupBankResponseDTO",
    "ImportedBankAccountDTO",
]
