"""Tests for TransactionEncoder."""

from decimal import Decimal

import pytest

from swen_ml.inference.encoder import TransactionEncoder


class TestBuildText:
    """Tests for text construction.

    Note: Amount is kept in the API for future use but currently not included
    in the embedding text. The text format focuses on counterparty, purpose,
    and reference for semantic matching.
    """

    def test_expense_with_counterparty(self) -> None:
        """Test expense transaction with counterparty."""
        # We don't need the full encoder for this test
        encoder = object.__new__(TransactionEncoder)

        text = TransactionEncoder.build_text(
            encoder,
            purpose="REWE SAGT DANKE 12345",
            amount=Decimal("-45.67"),
            counterparty_name="REWE",
            reference=None,
        )

        # Amount is intentionally not included in embedding text
        assert text == "REWE | REWE 12345"

    def test_income_with_counterparty(self) -> None:
        """Test income transaction."""
        encoder = object.__new__(TransactionEncoder)

        text = TransactionEncoder.build_text(
            encoder,
            purpose="GEHALT JANUAR",
            amount=Decimal("2500.00"),
            counterparty_name="ARBEITGEBER GMBH",
            reference=None,
        )

        # Amount is intentionally not included - format: counterparty | purpose
        assert text == "ARBEITGEBER | GEHALT JANUAR"

    def test_missing_counterparty(self) -> None:
        """Test transaction without counterparty."""
        encoder = object.__new__(TransactionEncoder)

        text = TransactionEncoder.build_text(
            encoder,
            purpose="ÜBERWEISUNG",
            amount=Decimal("-100.00"),
            counterparty_name=None,
            reference=None,
        )

        # Only purpose when no counterparty
        assert text == "ÜBERWEISUNG"

    def test_with_reference(self) -> None:
        """Test transaction with reference."""
        encoder = object.__new__(TransactionEncoder)

        text = TransactionEncoder.build_text(
            encoder,
            purpose="NETFLIX.COM",
            amount=Decimal("-12.99"),
            counterparty_name="NETFLIX",
            reference="MREF-12345",
        )

        assert text == "NETFLIX | NETFLIX.COM | MREF-12345"

    def test_noise_removal(self) -> None:
        """Test that banking noise patterns are removed."""
        encoder = object.__new__(TransactionEncoder)

        text = TransactionEncoder.build_text(
            encoder,
            purpose="REWE SAGT DANKE vom 15.01.2026",
            amount=Decimal("-45.67"),
            counterparty_name="REWE.Berlin.Friedrichsh",
            reference=None,
        )

        # Noise like "SAGT DANKE" and dates should be removed
        # Counterparty should be extracted as first part before delimiter
        assert "SAGT DANKE" not in text
        assert "15.01.2026" not in text


class TestBuildKeywordText:
    """Tests for keyword text construction (used for description matching)."""

    def test_basic_keyword_text(self) -> None:
        """Test keyword text generation."""
        encoder = object.__new__(TransactionEncoder)

        text = TransactionEncoder.build_keyword_text(
            encoder,
            purpose="REWE SAGT DANKE 12345",
            counterparty_name="REWE",
        )

        # Keyword text is simpler, without pipe delimiters
        assert "REWE" in text
        assert "SAGT DANKE" not in text  # Noise removed

    def test_keyword_text_without_counterparty(self) -> None:
        """Test keyword text without counterparty."""
        encoder = object.__new__(TransactionEncoder)

        text = TransactionEncoder.build_keyword_text(
            encoder,
            purpose="ÜBERWEISUNG MIETE",
            counterparty_name=None,
        )

        assert text == "ÜBERWEISUNG MIETE"
