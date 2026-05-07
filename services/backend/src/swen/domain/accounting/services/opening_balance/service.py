"""Domain service for opening balance operations.

Merges the query and adjustment concerns into a single cohesive service that
lives in the domain layer. Replaces:
  - ``application/queries/integration/opening_balance_query.py``
  - ``application/services/opening_balance_adjustment_service.py``
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
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
    from swen.domain.banking.value_objects import BankTransaction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpeningBalanceOutcome:
    """Outcome of an attempt to create an opening balance for an IBAN.

    Returned from :meth:`OpeningBalanceService.try_create_for_first_sync`.
    """

    created: bool
    amount: Optional[Decimal] = None


class OpeningBalanceService:
    """Domain service that coordinates opening balance reads and writes.

    Owns:
    - Querying whether an opening balance already exists for an IBAN
    - Querying whether an adjustment has been created for a given transfer
    - Creating adjustment transactions when internal transfers predate an OB
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

    # ------------------------------------------------------------------
    # First-sync provisioning
    # ------------------------------------------------------------------

    async def has_for_iban(self, iban: str) -> bool:
        """Return ``True`` iff an opening balance already exists for *iban*."""
        return await self.get_date_for_iban(iban) is not None

    async def try_create_for_first_sync(  # noqa: PLR0911
        self,
        iban: str,
        current_balance: Decimal,
        bank_transactions: list[BankTransaction],
    ) -> OpeningBalanceOutcome:
        """Create an opening balance for *iban* if one does not yet exist.

        Uses :class:`OpeningBalanceCalculator` to back-calculate the opening
        balance amount from *current_balance* and the fetched
        *bank_transactions*. Persists the resulting transaction via the
        injected ``transaction_repository``.

        Returns an :class:`OpeningBalanceOutcome` describing whether an
        opening balance was created and, if so, with what amount.
        """
        if await self.has_for_iban(iban):
            logger.debug("Opening balance already exists for IBAN %s", iban)
            return OpeningBalanceOutcome(created=False)

        if not bank_transactions:
            logger.debug(
                "Skip opening balance: no transactions to derive a date for %s",
                iban,
            )
            return OpeningBalanceOutcome(created=False)

        asset_account = await self._account_repo.find_by_iban(iban)
        if asset_account is None:
            logger.warning(
                "Cannot create opening balance: no asset account found for %s",
                iban,
            )
            return OpeningBalanceOutcome(created=False)

        equity_account = await self._account_repo.find_by_account_number(
            WellKnownAccounts.OPENING_BALANCE_EQUITY,
        )
        if equity_account is None:
            logger.warning(
                "Cannot create opening balance: equity account %s not found",
                WellKnownAccounts.OPENING_BALANCE_EQUITY,
            )
            return OpeningBalanceOutcome(created=False)

        opening_balance = self._calculator.calculate_opening_balance(
            current_balance=current_balance,
            bank_transactions=bank_transactions,
        )
        balance_date = self._calculator.get_earliest_transaction_date(
            bank_transactions,
        )
        if balance_date is None:
            logger.warning("Cannot determine date for opening balance for %s", iban)
            return OpeningBalanceOutcome(created=False)

        currency = bank_transactions[0].currency

        txn = self._calculator.create_opening_balance_transaction(
            asset_account=asset_account,
            opening_balance_account=equity_account,
            amount=opening_balance,
            currency=currency,
            balance_date=balance_date,
            iban=iban,
            user_id=self._user_id,
        )

        if txn is None:
            logger.info("Opening balance is zero for %s; skipping", iban)
            return OpeningBalanceOutcome(created=False)

        await self._transaction_repo.save(txn)
        logger.info(
            "Created opening balance of %s %s for %s (date: %s)",
            opening_balance,
            currency,
            iban,
            balance_date.date(),
        )
        return OpeningBalanceOutcome(created=True, amount=opening_balance)
