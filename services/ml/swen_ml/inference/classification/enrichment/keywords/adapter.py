from __future__ import annotations

import logging
import re
from pathlib import Path

from .port import KeywordPort

logger = logging.getLogger(__name__)


class FileKeywordAdapter(KeywordPort):
    """Keyword enrichment adapter that loads keywords from text files."""

    def __init__(self, keywords_file: Path | None = None):
        if keywords_file is None:
            keywords_file = Path(__file__).parent / "keywords_de.txt"

        self.keywords_file = keywords_file
        self.keyword_map: dict[str, str] = {}

        # Load keywords on initialization
        self.load_keywords()

    def load_keywords(self) -> None:
        if not self.keywords_file.exists():
            logger.warning("Keywords file not found: %s", self.keywords_file)
            return

        self.keyword_map = {}

        with open(self.keywords_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Expected format: keyword -> enrichment text
                if "->" not in line:
                    logger.warning(
                        "Invalid format in %s line %d: %s",
                        self.keywords_file.name,
                        line_num,
                        line,
                    )
                    continue

                keyword, enrichment = line.split("->", 1)
                keyword = keyword.strip().lower()
                enrichment = enrichment.strip()

                if keyword and enrichment:
                    self.keyword_map[keyword] = enrichment

        logger.info(
            "Loaded %d keyword mappings from %s",
            len(self.keyword_map),
            self.keywords_file.name,
        )

    def enrich(self, text: str) -> str | None:
        """
        Check if text contains any keywords and return enrichment.

        Uses tokenization + set membership for O(m) performance where m is
        the number of words in text, instead of O(n*m) where n is keywords.
        """
        if not text:
            return None

        # Tokenize once: split by non-word characters, lowercase
        tokens = {token.lower() for token in re.findall(r"\w+", text)}

        # Check if any token matches a keyword (O(m) where m = tokens)
        for token in tokens:
            if token in self.keyword_map:
                enrichment = self.keyword_map[token]
                return enrichment

        return None
