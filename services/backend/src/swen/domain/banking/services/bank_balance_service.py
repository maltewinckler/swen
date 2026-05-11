"""Domain service for managing and refreshing bank account balances."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from swen.domain.banking.services.bank_fetch_service import BankFetchService

if TYPE_CHECKING:
    from decimal import Decimal

    from swen.domain.banking.repositories import (
        BankAccountRepository,
        BankCredentialRepository,
    )

logger = logging.getLogger(__name__)


class BankBalanceService:
    """Domain service for managing and refreshing bank account balances.

    Provides two complementary capabilities:
    - ``refresh_for_blz``: fetch and persist all account balances for a BLZ.
    - ``get_for_iban``: DB-first balance lookup for a specific IBAN with
      bank-fetch fallback.

    Non-fatal by design: ``refresh_for_blz`` catches all errors and logs a
    warning so that callers (e.g. SyncBankAccountsCommand) are not aborted.
    """

    def __init__(
        self,
        bank_fetch_service: BankFetchService,
        bank_account_repo: BankAccountRepository,
        credential_repo: BankCredentialRepository,
    ):
        self._bank_fetch_service = bank_fetch_service
        self._bank_account_repo = bank_account_repo
        self._credential_repo = credential_repo

    async def refresh_for_blz(self, blz: str) -> None:
        """Fetch all accounts for ``blz`` and persist their balances."""
        credentials = await self._credential_repo.find_by_blz(blz)
        if credentials is None:
            logger.warning(
                "Balance refresh skipped: no credentials found for BLZ %s", blz
            )
            return

        try:
            accounts = await self._bank_fetch_service.fetch_accounts(credentials)
            await self._bank_account_repo.save_accounts(accounts)
            logger.info("Refreshed balances for %d accounts", len(accounts))
        except Exception as e:
            logger.warning("Balance refresh failed for BLZ %s: %s", blz, e)

    async def get_for_iban(self, iban: str) -> Optional[Decimal]:
        """Return the current balance for ``iban`` from the DB, or ``None``.

        The balance is expected to be persisted by the time this is called
        (e.g. by ``BankConnectionCommand`` on initial import or by
        ``refresh_for_blz`` after a sync). Returns ``None`` when no stored
        balance is found.
        """
        return await self._bank_account_repo.find_balance(iban)
