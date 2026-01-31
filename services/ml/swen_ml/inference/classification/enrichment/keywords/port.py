from typing import Protocol


class KeywordPort(Protocol):
    """Port for keyword enrichment backends."""

    def load_keywords(self) -> None:
        """Load keyword lists with enrichment texts."""
        ...

    def enrich(self, text: str) -> str | None:
        """Enrich text with categorical keywords if a match is found."""
        ...
