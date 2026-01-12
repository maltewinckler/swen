"""Accounting commands - operations on chart of accounts and transactions."""

from swen.application.commands.accounting.create_account_command import (
    CreateAccountCommand,
)
from swen.application.commands.accounting.create_simple_transaction_command import (
    CreateSimpleTransactionCommand,
)
from swen.application.commands.accounting.create_transaction_command import (
    CreateTransactionCommand,
)
from swen.application.commands.accounting.delete_transaction_command import (
    DeleteTransactionCommand,
)
from swen.application.commands.accounting.edit_transaction_command import (
    EditTransactionCommand,
)
from swen.application.commands.accounting.generate_default_accounts_command import (
    ChartTemplate,
    GenerateDefaultAccountsCommand,
)
from swen.application.commands.accounting.post_transaction_command import (
    BulkPostTransactionsCommand,
    PostTransactionCommand,
    UnpostTransactionCommand,
)
from swen.application.commands.accounting.update_account_command import (
    DeactivateAccountCommand,
    DeleteAccountCommand,
    ParentAction,
    ReactivateAccountCommand,
    UpdateAccountCommand,
)

__all__ = [
    # Transaction commands (new paradigm)
    "CreateTransactionCommand",  # Primary: entry-based, multi-entry support
    "CreateSimpleTransactionCommand",  # Convenience: simple 2-entry with hints
    # Transaction lifecycle
    "BulkPostTransactionsCommand",
    "DeleteTransactionCommand",
    "EditTransactionCommand",
    "PostTransactionCommand",
    "UnpostTransactionCommand",
    # Account commands
    "ChartTemplate",
    "CreateAccountCommand",
    "DeactivateAccountCommand",
    "DeleteAccountCommand",
    "GenerateDefaultAccountsCommand",
    "ParentAction",
    "ReactivateAccountCommand",
    "UpdateAccountCommand",
]
