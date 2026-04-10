"""Repository interface for bank information."""

from abc import ABC, abstractmethod
from typing import Literal

from swen.domain.banking.value_objects.bank_info import BankInfo


class BankInfoRepository(ABC):
    """Repository for bank metadata (BLZ → name, BIC, etc.).

    This is a system-wide repository (not user-scoped).
    Bank information is populated at admin setup time from
    either the FinTS institute CSV or the Geldstrom API.
    """

    @abstractmethod
    async def find_by_blz(self, blz: str) -> BankInfo | None:
        """Find bank information by BLZ."""

    @abstractmethod
    async def find_all(self) -> list[BankInfo]:
        """Return all known banks."""

    @abstractmethod
    async def save_batch(
        self,
        banks: list[BankInfo],
        source: Literal["csv", "api"],
    ) -> int:
        """Upsert a batch of bank information records.

        Parameters
        ----------
        banks
            The bank info records to upsert.
        source
            Origin of the data (``'csv'`` or ``'api'``).

        Returns
        -------
        Number of records upserted.
        """

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of known banks."""
