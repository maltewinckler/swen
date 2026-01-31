from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from swen_ml_contracts import TransactionInput

if TYPE_CHECKING:
    from swen_ml.inference.classification.result import ClassificationResult

from .patterns import KNOWN_MERCHANTS, MERCHANT_PATTERN, STRIP_PREFIXES


@dataclass
class MerchantResult:
    """Result from merchant extraction for a single transaction."""

    transaction_id: UUID
    merchant: str | None
    counterparty: str | None


def extract_merchant(counterparty: str | None) -> str | None:
    """Extract normalized merchant name from counterparty string."""
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
    """Extract merchants for all transactions."""
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


class MerchantExtractor:
    """Extractor for merchant names from transaction counterparties.

    Stateless service that normalizes and extracts merchant names
    from counterparty strings using pattern matching.
    """

    def extract(self, transactions: list[TransactionInput]) -> list[MerchantResult]:
        """Extract merchant names from transactions.

        Args:
            transactions: Transactions to process

        Returns:
            List of MerchantResult, one per transaction
        """
        results: list[MerchantResult] = []

        for txn in transactions:
            merchant = extract_merchant(txn.counterparty_name)
            results.append(
                MerchantResult(
                    transaction_id=txn.transaction_id,
                    merchant=merchant,
                    counterparty=txn.counterparty_name,
                )
            )

        return results

    def extract_single(self, counterparty: str | None) -> str | None:
        """Extract merchant name from a single counterparty string."""
        return extract_merchant(counterparty)
