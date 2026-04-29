"""Filter value object for transaction queries."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransactionFilters(BaseModel):
    """Encapsulates filtering criteria for transaction queries.

    When a filter is default (None), it means "no filter" for that dimension.
    """

    model_config = ConfigDict(frozen=True)

    start_date: Optional[str] = None
    """Filter transactions on or after this date (ISO format)."""

    end_date: Optional[str] = None
    """Filter transactions on or before this date (ISO format)."""

    status: Optional[str] = None
    """Filter by status: 'posted', 'draft', or None for all."""

    account_id: Optional[UUID] = None
    """Filter to transactions involving this account."""

    exclude_internal_transfers: bool = False
    """If True, exclude internal transfers between own accounts."""

    source_filter: Optional[str] = None
    """Filter by source: 'bank_import', 'manual', 'opening_balance_adjustment', etc."""
