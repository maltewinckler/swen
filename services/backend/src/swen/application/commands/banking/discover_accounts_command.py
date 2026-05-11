"""Discovers accounts for a bank without any persistence.

Discovers accounts for a given bank and returns a DTO that is then passed back to the
frontend such that the user can rename the accounts to the need. Then, it is forwarded
to the import command which handles the actual import into our accounting domain.

This is purely a banking concern.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from swen.application.dtos.banking import (
    BankDiscoveryResultDTO,
    DiscoveredAccountDTO,
)
from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.banking.services import BankFetchService
from swen.infrastructure.banking.bank_connection_dispatcher import (
    BankConnectionDispatcher,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.banking.value_objects import BankAccount

logger = logging.getLogger(__name__)


class DiscoverAccountsCommand:
    """Discover accounts for a bank without any persistence."""

    def __init__(
        self,
        bank_fetch_service: BankFetchService,
        credential_repo: BankCredentialRepository,
    ):
        self._bank_fetch_service = bank_fetch_service
        self._credential_repo = credential_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> "DiscoverAccountsCommand":
        return cls(
            bank_fetch_service=BankFetchService(
                bank_adapter=BankConnectionDispatcher.from_factory(factory)
            ),
            credential_repo=factory.credential_repository(),
        )

    async def execute(self, blz: str) -> BankDiscoveryResultDTO:
        credentials = await self._credential_repo.find_by_blz(blz)
        if credentials is None:
            logger.warning("No credentials found for BLZ %s, discovery skipped.", blz)
            return BankDiscoveryResultDTO(blz=blz, accounts=[])
        tan_method, tan_medium = await self._credential_repo.get_tan_settings(blz)

        bank_accounts = await self._bank_fetch_service.fetch_accounts(
            credentials=credentials,
            tan_method=tan_method,
            tan_medium=tan_medium,
        )
        accounts = [
            DiscoveredAccountDTO(
                iban=acc.iban,
                default_name=self._generate_default_account_name(acc),
                account_number=acc.account_number,
                account_holder=acc.account_holder,
                account_type=acc.account_type,
                blz=acc.blz,
                bic=acc.bic,
                bank_name=acc.bank_name,
                currency=acc.currency,
                balance=str(acc.balance) if acc.balance else None,
                balance_date=acc.balance_date.isoformat() if acc.balance_date else None,
            )
            for acc in bank_accounts
        ]
        logger.debug("Discovered %s accounts for BLZ %s.", len(accounts), blz)
        return BankDiscoveryResultDTO(blz=blz, accounts=accounts)

    @staticmethod
    def _generate_default_account_name(bank_account: BankAccount) -> str:
        """
        Generate a user-friendly default account name.

        Format: "{Bank Name} - {Account Type}"
        Fallback: "{Account Holder} - {Account Type}"
        """
        if bank_account.bank_name:
            return f"{bank_account.bank_name} - {bank_account.account_type}"
        return f"{bank_account.account_holder} - {bank_account.account_type}"
