"""Integration domain repository interfaces."""

from swen.domain.integration.repositories.account_mapping_repository import (
    AccountMappingRepository,
)
from swen.domain.integration.repositories.counter_account_rule_repository import (
    CounterAccountRuleRepository,
)
from swen.domain.integration.repositories.transaction_import_repository import (
    TransactionImportRepository,
)

__all__ = [
    "AccountMappingRepository",
    "CounterAccountRuleRepository",
    "TransactionImportRepository",
]
