"""Query to look up bank information by BLZ."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.domain.banking.value_objects.bank_info import BankInfo

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.banking.repositories.bank_info_repository import (
        BankInfoRepository,
    )


class LookupBankQuery:
    """Look up bank metadata from the bank_information table."""

    def __init__(self, bank_info_repo: BankInfoRepository) -> None:
        self._repo = bank_info_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> LookupBankQuery:
        return cls(bank_info_repo=factory.bank_info_repository())

    async def execute(self, blz: str) -> BankInfo | None:
        """Find bank information by BLZ, or None if not found."""
        return await self._repo.find_by_blz(blz)

    async def list_all(self) -> list[BankInfo]:
        """Return all known banks."""
        return await self._repo.find_all()
