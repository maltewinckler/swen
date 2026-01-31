from dataclasses import dataclass
from typing import Protocol


@dataclass
class SearchResult:
    """A single search result from enrichment."""

    title: str
    content: str
    url: str
    score: float


class SearchPort(Protocol):
    """Port for search enrichment backends."""

    async def search(self, query: str) -> list[SearchResult]:
        """Execute search and return results."""
        ...
