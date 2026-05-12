"""Bank fetch service.

Owns the bank session lifecycle: connect, optional TAN configuration,
fetch, then disconnect (in ``try/finally``). Wraps a
:class:`BankConnectionPort` so callers never see infrastructure types.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from swen.domain.banking.ports import BankConnectionPort

if TYPE_CHECKING:
    from swen.domain.banking.value_objects import (
        BankAccount,
        BankCredentials,
        BankTransaction,
    )


class BankFetchService:
    """Domain service that owns the bank session lifecycle."""

    def __init__(self, bank_adapter: BankConnectionPort) -> None:
        self._adapter = bank_adapter

    async def fetch_transactions(  # noqa: PLR0913
        self,
        credentials: BankCredentials,
        iban: str,
        start_date: date,
        end_date: date,
        tan_method: Optional[str] = None,
        tan_medium: Optional[str] = None,
    ) -> list[BankTransaction]:
        """Fetch transactions for ``iban`` within ``[start_date, end_date]``.

        Connect-disconnect is owned here. Optional TAN settings are applied to
        the adapter before connecting. Disconnect runs in a ``finally`` block
        so the bank session is never leaked.
        """
        await self._configure_session(tan_method, tan_medium)
        await self._adapter.connect(credentials)
        try:
            return await self._adapter.fetch_transactions(
                account_iban=iban,
                start_date=start_date,
                end_date=end_date,
            )
        finally:
            await self._adapter.disconnect()

    async def fetch_accounts(
        self,
        credentials: BankCredentials,
        tan_method: Optional[str] = None,
        tan_medium: Optional[str] = None,
    ) -> list[BankAccount]:
        """Fetch accounts accessible with ``credentials``.

        Connect-disconnect is owned here. Disconnect always runs in a
        ``finally`` block.
        """
        await self._configure_session(tan_method, tan_medium)
        await self._adapter.connect(credentials)
        try:
            return await self._adapter.fetch_accounts()
        finally:
            await self._adapter.disconnect()

    async def _configure_session(
        self,
        tan_method: Optional[str],
        tan_medium: Optional[str],
    ) -> None:
        if tan_method:
            self._adapter.set_tan_method(tan_method)
        if tan_medium:
            self._adapter.set_tan_medium(tan_medium)
