"""Domain service for managing and refreshing bank account balances."""

from __future__ import annotations

import logging

from swen.domain.banking.ports import BankConnectionPort
from swen.domain.banking.repositories import (
    BankAccountRepository,
    BankCredentialRepository,
)

logger = logging.getLogger(__name__)


class BankBalanceService:
    """Refresh bank account balances via the bank adapter.

    Sits in the domain banking layer because it only orchestrates banking
    domain objects (BankAccount, credentials) through domain ports —
    it has no dependency on application or infrastructure concerns.

    Non-fatal by design: ``refresh_for_blz`` catches all errors and logs a
    warning so that callers (e.g. BatchSyncCommand) are not aborted.
    """

    def __init__(
        self,
        bank_adapter: BankConnectionPort,
        bank_account_repo: BankAccountRepository,
        credential_repo: BankCredentialRepository,
    ):
        self._adapter = bank_adapter
        self._bank_account_repo = bank_account_repo
        self._credential_repo = credential_repo

    async def refresh_for_blz(self, blz: str) -> None:
        """Connect to the bank, refresh all account balances, then disconnect."""
        credentials = await self._credential_repo.find_by_blz(blz)
        if credentials is None:
            logger.warning(
                "Balance refresh skipped: no credentials found for BLZ %s", blz
            )
            return

        try:
            await self._adapter.connect(credentials)
            try:
                accounts = await self._adapter.fetch_accounts()
                await self._bank_account_repo.save_accounts(accounts)
                logger.info("Refreshed balances for %d accounts", len(accounts))
            finally:
                await self._adapter.disconnect()
        except Exception as e:
            logger.warning("Balance refresh failed for BLZ %s: %s", blz, e)
