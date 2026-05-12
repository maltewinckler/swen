"""DTO for a single transaction import attempt result."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from swen.domain.integration.value_objects import ImportStatus

if TYPE_CHECKING:
    from swen.domain.accounting.aggregates import Transaction
    from swen.domain.banking.value_objects import BankTransaction


@dataclass(frozen=True)
class TransactionImportResult:
    """Result of a single transaction import attempt."""

    bank_transaction: BankTransaction
    status: ImportStatus
    accounting_transaction: Transaction | None = field(default=None)
    error_message: str | None = field(default=None)
    was_reconciled: bool = field(default=False)

    @property
    def is_success(self) -> bool:
        return self.status == ImportStatus.SUCCESS

    @property
    def is_duplicate(self) -> bool:
        return self.status == ImportStatus.DUPLICATE

    @property
    def is_failed(self) -> bool:
        return self.status == ImportStatus.FAILED

    @property
    def is_reconciled(self) -> bool:
        return self.was_reconciled
