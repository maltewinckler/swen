"""Query for opening balance information needed during reconciliation.

This query encapsulates the logic for finding opening balance dates and
checking for existing adjustments. These are operational concerns for
the reconciliation fix, not first-class domain concepts.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from swen.domain.shared.iban import normalize_iban

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.repositories import TransactionRepository


class OpeningBalanceQuery:
    """Query for opening balance information needed during reconciliation."""

    def __init__(self, transaction_repository: TransactionRepository):
        self._repo = transaction_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> OpeningBalanceQuery:
        return cls(transaction_repository=factory.transaction_repository())

    async def get_date_for_iban(self, iban: str) -> Optional[date]:
        """Find the opening balance date for an account by IBAN."""
        normalized = normalize_iban(iban)
        if not normalized:
            return None

        transactions = await self._repo.find_by_metadata(
            metadata_key="is_opening_balance",
            metadata_value=True,
        )

        for txn in transactions:
            txn_iban = normalize_iban(txn.get_metadata_raw("opening_balance_iban"))
            if txn_iban == normalized:
                return txn.date.date() if txn.date else None

        return None

    async def adjustment_exists_for_transfer(
        self,
        iban: str,
        transfer_hash: str,
    ) -> bool:
        normalized = normalize_iban(iban)
        if not normalized or not transfer_hash:
            return False

        # Query adjustment transactions
        transactions = await self._repo.find_with_filters(
            source_filter="opening_balance_adjustment",
        )

        for txn in transactions:
            txn_iban = normalize_iban(txn.get_metadata_raw("opening_balance_iban"))
            txn_hash = txn.get_metadata_raw("transfer_identity_hash")

            if txn_iban == normalized and txn_hash == transfer_hash:
                return True

        return False
