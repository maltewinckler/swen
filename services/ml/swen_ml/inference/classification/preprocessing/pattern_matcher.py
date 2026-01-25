"""Pattern matching: extract keywords from known patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swen_ml.inference.classification.context import (
        TransactionContext,
    )

# Keywords in purpose text that indicate categories
# Maps keyword -> category label for metadata
KEYWORDS: dict[str, str] = {
    # Housing
    "miete": "housing",
    "nebenkosten": "housing",
    "strom": "utilities",
    "gas": "utilities",
    "heizung": "utilities",
    "rundfunk": "utilities",
    "gez": "utilities",
    # Income
    "gehalt": "income",
    "lohn": "income",
    "bezuege": "income",
    # Refunds
    "erstattung": "refund",
    "rueckzahlung": "refund",
    "gutschrift": "refund",
    # Food
    "restaurant": "restaurant",
    "gastronomie": "restaurant",
    "lieferung": "delivery",
    # Transport
    "tankstelle": "fuel",
    "tanken": "fuel",
    "benzin": "fuel",
    "diesel": "fuel",
    # Subscriptions
    "abonnement": "subscription",
    "abo": "subscription",
    "mitgliedschaft": "membership",
    # Insurance
    "versicherung": "insurance",
    "beitrag": "contribution",
}


class PatternMatcher:
    """Preprocessor that adds matched keywords as metadata.

    Scans cleaned counterparty and purpose for known keywords
    and adds them to ctx.matched_keywords for use by classifiers.
    """

    name = "pattern_matcher"

    def __init__(self, keywords: dict[str, str] | None = None):
        self.keywords = keywords or KEYWORDS

    def _find_keywords(self, text: str) -> list[str]:
        """Find all matching keywords in text."""
        text_lower = text.lower()
        matched = []
        for keyword, label in self.keywords.items():
            if keyword in text_lower:
                matched.append(label)
        return list(set(matched))

    def process_batch(self, contexts: list[TransactionContext]) -> None:
        """Find keywords in all transactions."""
        for ctx in contexts:
            keywords: list[str] = []

            # Search in cleaned counterparty
            if ctx.cleaned_counterparty:
                keywords.extend(self._find_keywords(ctx.cleaned_counterparty))

            # Search in cleaned purpose
            if ctx.cleaned_purpose:
                keywords.extend(self._find_keywords(ctx.cleaned_purpose))

            ctx.matched_keywords = list(set(keywords))
