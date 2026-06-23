"""DTO for bank account reconciliation results."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, computed_field


class AccountReconciliationDTO(BaseModel):
    """Reconciliation result for a single bank account."""

    model_config = ConfigDict(frozen=True)

    iban: str
    account_name: str
    accounting_account_id: str
    currency: str

    bank_balance: Decimal
    bank_balance_date: Optional[datetime]
    last_sync_at: Optional[datetime]

    bookkeeping_balance: Decimal

    discrepancy: Decimal
    is_reconciled: bool

    @computed_field
    @property
    def discrepancy_abs(self) -> Decimal:
        return abs(self.discrepancy)


class ReconciliationResultDTO(BaseModel):
    """Aggregated reconciliation result for all bank accounts."""

    accounts: tuple[AccountReconciliationDTO, ...]
    total_accounts: int
    reconciled_count: int
    discrepancy_count: int

    @computed_field
    @property
    def all_reconciled(self) -> bool:
        return self.discrepancy_count == 0

    @computed_field
    @property
    def has_discrepancies(self) -> bool:
        return self.discrepancy_count > 0
