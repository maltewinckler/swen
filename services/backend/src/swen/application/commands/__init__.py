"""Command layer - write operations that mutate state.

Commands follow the CQRS pattern and represent user intentions
to change system state. They orchestrate domain services and
return structured results via DTOs.

Commands are organized by domain:
- accounting: Chart of accounts and transaction management
- banking: Bank connections and credential management
- integration: Sync orchestration between banking and accounting
- settings: User settings/preferences management
- system: Maintenance and integrity operations
"""

from swen.application.commands.accounting import (
    BulkPostTransactionsCommand,
    ChartTemplate,
    CreateAccountCommand,
    CreateSimpleTransactionCommand,
    CreateTransactionCommand,
    DeactivateAccountCommand,
    DeleteTransactionCommand,
    EditTransactionCommand,
    GenerateDefaultAccountsCommand,
    PostTransactionCommand,
    UnpostTransactionCommand,
    UpdateAccountCommand,
)
from swen.application.commands.banking import (
    BankConnectionCommand,
    StoreCredentialsCommand,
)
from swen.application.commands.integration import (
    BatchSyncCommand,
    TransactionSyncCommand,
)
from swen.application.commands.settings import (
    ResetUserSettingsCommand,
    UpdateUserSettingsCommand,
)
from swen.application.commands.system import (
    FixIntegrityIssuesCommand,
    FixResult,
)

__all__ = [
    # Accounting - Transaction Commands
    "CreateTransactionCommand",
    "CreateSimpleTransactionCommand",
    "BulkPostTransactionsCommand",
    "DeleteTransactionCommand",
    "EditTransactionCommand",
    "PostTransactionCommand",
    "UnpostTransactionCommand",
    # Accounting - Account Commands
    "ChartTemplate",
    "CreateAccountCommand",
    "DeactivateAccountCommand",
    "GenerateDefaultAccountsCommand",
    "UpdateAccountCommand",
    # Banking
    "BankConnectionCommand",
    "StoreCredentialsCommand",
    # Integration
    "BatchSyncCommand",
    "TransactionSyncCommand",
    # System
    "FixIntegrityIssuesCommand",
    "FixResult",
    # Settings
    "ResetUserSettingsCommand",
    "UpdateUserSettingsCommand",
]
