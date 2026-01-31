"""Search enrichment for classification pipeline."""

from .keywords import FileKeywordAdapter, KeywordPort
from .search import SearchPort, SearchResult, SearXNGAdapter
from .service import Enrichment, EnrichmentService, extract_enrichment_text

__all__ = [
    "SearchPort",
    "SearchResult",
    "SearXNGAdapter",
    "KeywordPort",
    "FileKeywordAdapter",
    "EnrichmentService",
    "Enrichment",
    "extract_enrichment_text",
]
