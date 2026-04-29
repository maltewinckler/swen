"""Banking domain SQLAlchemy repositories."""

from swen.infrastructure.persistence.sqlalchemy.repositories.banking.bank_account_repository import (  # NOQA: E501
    BankAccountRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking.bank_credential_repository import (  # NOQA: E501
    BankCredentialRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking.bank_info_repository_sqlalchemy import (  # NOQA: E501
    BankInfoRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking.bank_transaction_repository import (  # NOQA: E501
    BankTransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking.geldstrom_api.geldstrom_api_config_repository_sqlalchemy import (  # NOQA: E501
    GeldstromApiConfigRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking.local_fints.config_repository_sqlalchemy import (  # NOQA: E501
    FinTSConfigRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking.local_fints.endpoint_repository_sqlalchemy import (  # NOQA: E501
    FinTSEndpointRepositorySQLAlchemy,
)

__all__ = [
    "BankAccountRepositorySQLAlchemy",
    "BankCredentialRepositorySQLAlchemy",
    "BankInfoRepositorySQLAlchemy",
    "BankTransactionRepositorySQLAlchemy",
    "FinTSConfigRepositorySQLAlchemy",
    "FinTSEndpointRepositorySQLAlchemy",
    "GeldstromApiConfigRepositorySQLAlchemy",
]
