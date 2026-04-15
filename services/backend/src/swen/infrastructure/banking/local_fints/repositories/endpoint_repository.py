"""Repository for FinTS endpoint URLs.

This is NOT a domain port. Only the local FinTS adapter needs
endpoint URLs; the Geldstrom API resolves endpoints internally.
"""

from abc import ABC, abstractmethod


class FinTSEndpointRepository(ABC):
    """Look up and persist FinTS server URLs keyed by BLZ."""

    @abstractmethod
    async def find_by_blz(self, blz: str) -> str | None:
        """Return the FinTS endpoint URL for the given BLZ, or None."""
        ...

    @abstractmethod
    async def save_batch(self, endpoints: dict[str, str]) -> int:
        """Upsert a batch of BLZ → endpoint_url mappings.

        Returns the number of records upserted.
        """
        ...
