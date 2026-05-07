"""Bank fetch service.

Owns the bank session lifecycle for the sync stack: connect, optional TAN
configuration, fetch, then disconnect (in `try/finally`). Wraps a
:class:`BankConnectionPort` so application callers never see infrastructure
types.
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from swen.domain.banking.ports import BankConnectionPort

if TYPE_CHECKING:
    from swen.application.dtos.integration.sync_period import SyncPeriod
    from swen.application.factories import RepositoryFactory
    from swen.domain.banking.value_objects import (
        BankAccount,
        BankCredentials,
        BankTransaction,
        TANChallenge,
    )


TanCallback = Callable[["TANChallenge"], "str | Awaitable[str]"]


class BankFetchService:
    """Application service that owns the bank session lifecycle."""

    def __init__(self, bank_adapter: BankConnectionPort) -> None:
        self._adapter = bank_adapter

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> BankFetchService:
        """Build the service via the repository factory's bank connection port."""
        return cls(bank_adapter=factory.bank_connection_port())

    async def fetch_transactions(  # noqa: PLR0913
        self,
        credentials: BankCredentials,
        iban: str,
        period: SyncPeriod,
        tan_method: Optional[str] = None,
        tan_medium: Optional[str] = None,
        tan_callback: Optional[TanCallback] = None,
    ) -> list[BankTransaction]:
        """Fetch transactions for `iban` within `period`.

        Connect-disconnect is owned here. Optional TAN settings (method/medium)
        and the TAN callback are applied to the adapter before connecting.
        Disconnect runs in a `finally` block so the bank session is never leaked.
        """
        await self._configure_session(tan_method, tan_medium, tan_callback)
        await self._adapter.connect(credentials)
        try:
            return await self._adapter.fetch_transactions(
                account_iban=iban,
                start_date=period.start_date,
                end_date=period.end_date,
            )
        finally:
            await self._adapter.disconnect()

    async def fetch_accounts(
        self,
        credentials: BankCredentials,
        tan_callback: Optional[TanCallback] = None,
    ) -> list[BankAccount]:
        """Fetch accounts accessible with `credentials`.

        Connect-disconnect is owned here. The optional TAN callback is applied
        before connecting; disconnect always runs in a `finally` block.
        """
        await self._configure_session(None, None, tan_callback)
        await self._adapter.connect(credentials)
        try:
            return await self._adapter.fetch_accounts()
        finally:
            await self._adapter.disconnect()

    async def _configure_session(
        self,
        tan_method: Optional[str],
        tan_medium: Optional[str],
        tan_callback: Optional[TanCallback],
    ) -> None:
        if tan_method:
            self._adapter.set_tan_method(tan_method)
        if tan_medium:
            self._adapter.set_tan_medium(tan_medium)
        if tan_callback is not None:
            await self._adapter.set_tan_callback(
                self._wrap_tan_callback(tan_callback),
            )

    @staticmethod
    def _wrap_tan_callback(
        callback: TanCallback,
    ) -> Callable[[TANChallenge], Awaitable[str]]:
        """Adapt a sync-or-async TAN callback into an awaitable callback."""

        @wraps(callback)
        async def _async_callback(challenge: TANChallenge) -> str:
            result = callback(challenge)
            if inspect.isawaitable(result):
                return await result  # type: ignore[func-returns-value]
            return result  # type: ignore[return-value,arg-type]

        return _async_callback
