"""DTOs for account statistics queries."""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccountStatsResult(BaseModel):
    """Result of account statistics query."""

    model_config = ConfigDict(frozen=True)

    # Account identification
    account_id: UUID
    account_name: str
    account_number: str
    account_type: str  # 'ASSET', 'LIABILITY', 'INCOME', 'EXPENSE', 'EQUITY'
    currency: str

    # Balance information
    balance: Decimal
    balance_includes_drafts: bool

    # Transaction statistics
    transaction_count: int
    posted_count: int
    draft_count: int

    # Flow statistics (within the queried period)
    total_debits: Decimal
    total_credits: Decimal
    net_flow: Decimal  # debits - credits (for assets: positive = money in)

    # Activity timestamps
    first_transaction_date: Optional[date]
    last_transaction_date: Optional[date]

    # Period info
    period_days: Optional[int]
    period_start: Optional[date]
    period_end: Optional[date]
