"""Current balance helper.

Resolves the current balance for an IBAN with a DB-first read and a
bank-fetch-with-persistence-back fallback. Lives in the application layer
because it composes a domain repository with the application-level
:class:`BankFetchService`; this keeps the domain
:class:`OpeningBalanceService` free of any
:class:`BankConnectionPort` dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from swen.application.services.integration.bank_fetch_service import BankFetchService

if TYPE_CHECKING:
    from decimal import Decimal

    from swen.application.factories import RepositoryFactory
    from swen.domain.banking.repositories import BankAccountRepository
    from swen.domain.banking.value_objects import BankCredentials


class CurrentBalanceService:
    """Resolve the current balance for an IBAN."""

    def __init__(
        self,
        bank_account_repo: BankAccountRepository,
        bank_fetch_service: BankFetchService,
    ) -> None:
        self._bank_account_repo = bank_account_repo
        self._bank_fetch_service = bank_fetch_service

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> CurrentBalanceService:
        """Build the service via the repository factory."""
        return cls(
            bank_account_repo=factory.bank_account_repository(),
            bank_fetch_service=BankFetchService.from_factory(factory),
        )

    async def for_iban(
        self,
        iban: str,
        credentials: BankCredentials,
    ) -> Optional[Decimal]:
        """Return the current balance for ``iban`` or ``None``.

        DB-first: when ``bank_account_repo.find_balance(iban)`` returns a
        value, it is returned without touching the bank. On miss, fetch
        accounts from the bank, persist them via
        ``bank_account_repo.save_accounts(...)`` so subsequent flows can
        find the ``BankAccount`` records by IBAN, and return the matching
        IBAN's balance from the fetched-and-persisted set. Returns
        ``None`` when no balance is determinable.
        """
        stored = await self._bank_account_repo.find_balance(iban)
        if stored is not None:
            return stored

        accounts = await self._bank_fetch_service.fetch_accounts(credentials)
        await self._bank_account_repo.save_accounts(accounts)

        for account in accounts:
            if account.iban == iban and account.balance is not None:
                return account.balance
        return None
