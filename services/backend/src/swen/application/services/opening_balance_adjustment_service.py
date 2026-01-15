"""Application service for creating opening balance adjustments.

This service orchestrates the creation of opening balance adjustments when
internal transfers are discovered that predate the counterparty account's
opening balance date.

The problem this solves:
- Account A syncs first with transactions from date X onwards
- Account A's opening balance is calculated correctly for date X
- Account B syncs later with transactions going back to date Y (where Y < X)
- Transfers from B to A between Y and X would double-count in A's balance
- This service creates adjustment entries to correct A's opening balance
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from swen.application.queries.integration import OpeningBalanceQuery
from swen.domain.accounting.entities import Account
from swen.domain.accounting.services import OpeningBalanceService
from swen.domain.accounting.well_known_accounts import WellKnownAccounts

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.ports.identity import CurrentUser
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )

logger = logging.getLogger(__name__)


class OpeningBalanceAdjustmentService:
    """Application service for creating opening balance adjustments."""

    def __init__(
        self,
        account_repository: AccountRepository,
        transaction_repository: TransactionRepository,
        opening_balance_query: OpeningBalanceQuery,
        current_user: CurrentUser,
    ):
        self._account_repo = account_repository
        self._transaction_repo = transaction_repository
        self._ob_query = opening_balance_query
        self._user_id = current_user.user_id
        self._opening_balance_service = OpeningBalanceService()

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> OpeningBalanceAdjustmentService:
        return cls(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            opening_balance_query=OpeningBalanceQuery.from_factory(factory),
            current_user=factory.current_user,
        )

    async def create_adjustment_if_needed(  # NOQA: PLR0913
        self,
        counterparty_account: Account,
        counterparty_iban: str,
        transfer_amount: Decimal,
        transfer_date: date,
        is_incoming_to_counterparty: bool,
        transfer_hash: Optional[str] = None,
    ) -> bool:
        # Check idempotency - has this adjustment already been created?
        if transfer_hash:
            already_exists = await self._ob_query.adjustment_exists_for_transfer(
                iban=counterparty_iban,
                transfer_hash=transfer_hash,
            )
            if already_exists:
                logger.debug(
                    "Opening balance adjustment already exists for transfer %s",
                    transfer_hash,
                )
                return False

        # Get the opening balance equity account
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

        # Convert date to datetime for the transaction
        adjustment_datetime = datetime.combine(
            transfer_date,
            time.min,
            timezone.utc,
        )

        # Create the adjustment using the domain service
        adjustment_txn = (
            self._opening_balance_service.create_opening_balance_adjustment(
                asset_account=counterparty_account,
                opening_balance_account=equity_account,
                adjustment_amount=adjustment_amount,
                adjustment_date=adjustment_datetime,
                iban=counterparty_iban,
                user_id=self._user_id,
                related_transfer_hash=transfer_hash,
            )
        )

        if adjustment_txn is None:
            logger.debug(
                "No adjustment needed for transfer (amount was zero)",
            )
            return False

        # Persist the adjustment
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
