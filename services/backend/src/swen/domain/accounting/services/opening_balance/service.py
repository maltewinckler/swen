"""Domain service for opening balance operations.

Merges the query and adjustment concerns into a single cohesive service that
lives in the domain layer. Replaces:
  - ``application/queries/integration/opening_balance_query.py``
  - ``application/services/opening_balance_adjustment_service.py``
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from swen.domain.accounting.services.opening_balance.calculator import (
    OpeningBalanceCalculator,
)
from swen.domain.accounting.value_objects import TransactionFilters
from swen.domain.accounting.well_known_accounts import WellKnownAccounts
from swen.domain.shared.iban import normalize_iban

if TYPE_CHECKING:
    from swen.domain.accounting.entities import Account
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )

logger = logging.getLogger(__name__)


class OpeningBalanceService:
    """Domain service that coordinates opening balance reads and writes.

    Owns:
    - Querying whether an opening balance already exists for an IBAN
    - Querying whether an adjustment has been created for a given transfer
    - Creating adjustment transactions when internal transfers predate an OB

    Layer: Domain — depends only on domain repositories (interfaces), not
    on infrastructure or application concerns.
    """

    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        user_id: UUID,
    ):
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._user_id = user_id
        self._calculator = OpeningBalanceCalculator()

    # ------------------------------------------------------------------
    # Query helpers (previously OpeningBalanceQuery)
    # ------------------------------------------------------------------

    async def get_date_for_iban(self, iban: str) -> Optional[date]:
        """Return the opening balance date for *iban*, or ``None`` if not found."""
        normalized = normalize_iban(iban)
        if not normalized:
            return None

        transactions = await self._transaction_repo.find_by_metadata(
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
        """Return ``True`` if an OB adjustment for *transfer_hash* already exists."""
        normalized = normalize_iban(iban)
        if not normalized or not transfer_hash:
            return False

        filters = TransactionFilters(source_filter="opening_balance_adjustment")
        transactions = await self._transaction_repo.find_with_filters(filters)

        for txn in transactions:
            txn_iban = normalize_iban(txn.get_metadata_raw("opening_balance_iban"))
            txn_hash = txn.get_metadata_raw("transfer_identity_hash")

            if txn_iban == normalized and txn_hash == transfer_hash:
                return True

        return False

    # ------------------------------------------------------------------
    # Write operations (previously OpeningBalanceAdjustmentService)
    # ------------------------------------------------------------------

    async def create_adjustment_if_needed(  # NOQA: PLR0913
        self,
        counterparty_account: Account,
        counterparty_iban: str,
        transfer_amount: Decimal,
        transfer_date: date,
        is_incoming_to_counterparty: bool,
        transfer_hash: Optional[str] = None,
    ) -> bool:
        """Create an OB adjustment if one does not yet exist for *transfer_hash*.

        Returns ``True`` when an adjustment was created, ``False`` otherwise.
        """
        if transfer_hash:
            already_exists = await self.adjustment_exists_for_transfer(
                iban=counterparty_iban,
                transfer_hash=transfer_hash,
            )
            if already_exists:
                logger.debug(
                    "Opening balance adjustment already exists for transfer %s",
                    transfer_hash,
                )
                return False

        equity_account = await self._account_repo.find_by_account_number(
            WellKnownAccounts.OPENING_BALANCE_EQUITY,
        )
        if not equity_account:
            logger.warning(
                "Cannot create opening balance adjustment: equity account %s not found",
                WellKnownAccounts.OPENING_BALANCE_EQUITY,
            )
            return False

        # Determine adjustment direction:
        # - Incoming transfer to counterparty: their OB already includes it,
        #   so we need to REDUCE their OB (positive adjustment)
        # - Outgoing transfer from counterparty: their OB doesn't include it,
        #   so we need to INCREASE their OB (negative adjustment)
        adjustment_amount = (
            transfer_amount if is_incoming_to_counterparty else -transfer_amount
        )

        adjustment_datetime = datetime.combine(
            transfer_date,
            time.min,
            timezone.utc,
        )

        adjustment_txn = self._calculator.create_opening_balance_adjustment(
            asset_account=counterparty_account,
            opening_balance_account=equity_account,
            adjustment_amount=adjustment_amount,
            adjustment_date=adjustment_datetime,
            iban=counterparty_iban,
            user_id=self._user_id,
            related_transfer_hash=transfer_hash,
        )

        if adjustment_txn is None:
            logger.debug("No adjustment needed for transfer (amount was zero)")
            return False

        await self._transaction_repo.save(adjustment_txn)

        direction = "incoming" if is_incoming_to_counterparty else "outgoing"
        logger.info(
            "Created opening balance adjustment of %s EUR for %s (%s transfer on %s)",
            adjustment_amount,
            counterparty_account.name,
            direction,
            transfer_date,
        )

        return True
