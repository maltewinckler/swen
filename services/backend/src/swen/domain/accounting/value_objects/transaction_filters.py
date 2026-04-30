"""Filter value object for transaction queries."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransactionFilters(BaseModel):
    """Filter criteria for transaction queries. None means no filter for that field."""

    start_date: Optional[str] = None  # Iso format
    end_date: Optional[str] = None  # Iso format
    status: Optional[str] = None  #  'posted', 'draft', or None for all
    account_id: Optional[UUID] = None
    exclude_internal_transfers: bool = False
    # 'bank_import', 'manual', 'opening_balance_adjustment', etc.
    source_filter: Optional[str] = None

    model_config = ConfigDict(frozen=True)
