"""Merchant extraction orchestrator.

This orchestrator is stateless - it doesn't need SharedInfrastructure.
It provides a simple wrapper around the extract_merchant function.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from swen_ml_contracts import TransactionInput

from .extractor import extract_merchant


@dataclass
class MerchantResult:
    """Result from merchant extraction."""

    transaction_id: UUID
    merchant: str | None
    counterparty: str | None


class MerchantOrchestrator:
    """Application service for merchant extraction.

    This orchestrator is stateless - no dependencies needed.
    Provides a batch interface for extracting merchant names.
    """

    def extract(
        self,
        transactions: list[TransactionInput],
    ) -> list[MerchantResult]:
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
