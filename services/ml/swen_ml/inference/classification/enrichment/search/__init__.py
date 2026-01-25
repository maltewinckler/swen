"""Search module for enrichment backends."""

from .port import SearchPort, SearchResult
from .searxng import SearXNGAdapter

__all__ = [
    "SearchPort",
    "SearchResult",
    "SearXNGAdapter",
]
