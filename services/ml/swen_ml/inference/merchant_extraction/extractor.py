"""Merchant name extraction from transaction counterparty."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from swen_ml.inference.classification.result import ClassificationResult

from .patterns import KNOWN_MERCHANTS, MERCHANT_PATTERN, STRIP_PREFIXES


def extract_merchant(counterparty: str | None) -> str | None:
    """Extract normalized merchant name from counterparty string.

    Examples:
        "REWE.Filiale.Nord/Hamburg" -> "REWE"
        "PAYPAL..SPOTIFY/35314369001" -> "SPOTIFY"
        "Stadtwerke Hamburg" -> "STADTWERKE"
    """
    if not counterparty:
        return None

    text = counterparty.strip().upper()

    # Handle PayPal-style: "PAYPAL..MERCHANT/..."
    if text.startswith("PAYPAL"):
        parts = re.split(r"[./]+", text)
        for part in parts[1:]:  # Skip PAYPAL
            if part and part not in STRIP_PREFIXES and len(part) > 2:
                return part
        return None

    # Standard extraction
    match = MERCHANT_PATTERN.match(text)
    if match:
        merchant = match.group(1).upper()
        if merchant not in STRIP_PREFIXES:
            return merchant

    return None


def extract_merchants(
    results: list[ClassificationResult],
    counterparties: dict[UUID, str | None],
) -> dict[UUID, str | None]:
    """Extract merchants for all transactions.

    Args:
        results: Classification results with transaction IDs
        counterparties: Map of transaction_id -> cleaned_counterparty

    Returns:
        Map of transaction_id -> extracted merchant name
    """
    merchants: dict[UUID, str | None] = {}

    for result in results:
        counterparty = counterparties.get(result.transaction_id)
        merchants[result.transaction_id] = extract_merchant(counterparty)

    return merchants


def is_known_merchant(merchant: str | None) -> bool:
    """Check if merchant is in the known merchants list."""
    if not merchant:
        return False
    return merchant.upper() in KNOWN_MERCHANTS
