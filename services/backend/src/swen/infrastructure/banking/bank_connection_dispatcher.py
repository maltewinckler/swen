"""Bank connection dispatcher - routes to the active FinTS provider adapter.

This dispatcher implements BankConnectionPort and delegates all calls to
the currently active adapter (local GeldstromAdapter or GeldstromApiAdapter),
determined lazily from the Geldstrom API configuration.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from swen.domain.banking.ports.bank_connection_port import BankConnectionPort
from swen.domain.banking.value_objects.bank_account import BankAccount
from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.domain.banking.value_objects.bank_transaction import BankTransaction
from swen.domain.banking.value_objects.tan_challenge import TANChallenge
from swen.domain.banking.value_objects.tan_method import TANMethod
from swen.infrastructure.banking.geldstrom_api.adapter import (
    GeldstromApiAdapter,
)
from swen.infrastructure.banking.local_fints.adapter import (
    GeldstromAdapter,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.infrastructure.banking.geldstrom_api.config_repository import (
        GeldstromApiConfigRepository,
    )

logger = logging.getLogger(__name__)


class BankConnectionDispatcher(BankConnectionPort):
    """Routes bank operations to the active FinTS provider adapter.

    Lazily resolves which adapter is active (local FinTS library vs
    Geldstrom API) on the first async call. Sync calls (set_tan_method,
    set_tan_medium) are buffered and applied when the adapter is resolved.

    Extensibility: When PSD2/XS2A or other connectors are added, only
    this dispatcher and a new adapter need to change. The application
    layer remains untouched.
    """

    def __init__(
        self,
        fints_adapter: BankConnectionPort,
        api_adapter: BankConnectionPort,
        geldstrom_api_config_repo: GeldstromApiConfigRepository,
    ) -> None:
        self._fints_adapter = fints_adapter
        self._api_adapter = api_adapter
        self._config_repo = geldstrom_api_config_repo
        self._resolved: BankConnectionPort | None = None

        # Buffered sync settings (applied on resolve)
        self._buffered_tan_method: str | None = None
        self._buffered_tan_medium: str | None = None

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> BankConnectionDispatcher:
        return cls(
            fints_adapter=GeldstromAdapter(
                config_repository=factory.fints_config_repository(),
                fints_endpoint_repo=factory.fints_endpoint_repository(),
            ),
            api_adapter=GeldstromApiAdapter(
                config_repository=factory.geldstrom_api_config_repository(),
            ),
            geldstrom_api_config_repo=(factory.geldstrom_api_config_repository()),
        )

    async def _resolve_adapter(self) -> BankConnectionPort:
        """Resolve and cache the active adapter on first use."""
        if self._resolved is not None:
            return self._resolved

        is_api_active = await self._config_repo.is_active()

        if is_api_active:
            logger.info("Using Geldstrom API adapter")
            self._resolved = self._api_adapter
        else:
            logger.info("Using local FinTS adapter")
            self._resolved = self._fints_adapter

        # Apply buffered TAN settings
        if self._buffered_tan_method:
            self._resolved.set_tan_method(self._buffered_tan_method)
        if self._buffered_tan_medium:
            self._resolved.set_tan_medium(self._buffered_tan_medium)

        return self._resolved

    async def connect(self, credentials: BankCredentials) -> bool:
        adapter = await self._resolve_adapter()
        return await adapter.connect(credentials)

    async def fetch_accounts(self) -> list[BankAccount]:
        adapter = await self._resolve_adapter()
        return await adapter.fetch_accounts()

    async def fetch_transactions(
        self,
        account_iban: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> list[BankTransaction]:
        adapter = await self._resolve_adapter()
        return await adapter.fetch_transactions(
            account_iban,
            start_date,
            end_date,
        )

    async def disconnect(self) -> None:
        adapter = await self._resolve_adapter()
        await adapter.disconnect()

    async def set_tan_callback(
        self,
        callback: Callable[[TANChallenge], Awaitable[str]],
    ) -> None:
        adapter = await self._resolve_adapter()
        await adapter.set_tan_callback(callback)

    async def get_tan_methods(
        self,
        credentials: BankCredentials,
    ) -> list[TANMethod]:
        adapter = await self._resolve_adapter()
        return await adapter.get_tan_methods(credentials)

    # ═══════════════════════════════════════════════════════════════
    #          BankConnectionPort — sync methods (buffered)
    # ═══════════════════════════════════════════════════════════════

    def is_connected(self) -> bool:
        if self._resolved is not None:
            return self._resolved.is_connected()
        return False

    def set_tan_method(self, tan_method: str) -> None:
        self._buffered_tan_method = tan_method
        if self._resolved is not None:
            self._resolved.set_tan_method(tan_method)

    def set_tan_medium(self, tan_medium: str) -> None:
        self._buffered_tan_medium = tan_medium
        if self._resolved is not None:
            self._resolved.set_tan_medium(tan_medium)
