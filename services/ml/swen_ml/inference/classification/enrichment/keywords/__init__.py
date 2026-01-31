"""Keyword-based enrichment for classification pipeline."""

from .adapter import FileKeywordAdapter
from .port import KeywordPort

__all__ = [
    "KeywordPort",
    "FileKeywordAdapter",
]
