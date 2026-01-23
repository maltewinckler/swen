"""Tests for TransactionEncoder text building."""

from decimal import Decimal

from swen_ml.inference.encoding.encoder import NOISE_REGEX


class TestBuildText:
    """Tests for text construction.

    Note: Amount is kept in the API for future use but currently not included
    in the embedding text. The text format focuses on counterparty, purpose,
    and reference for semantic matching.
    """

    def _build_text(
        self,
        purpose: str,
        amount: Decimal,
        counterparty_name: str | None,
        reference: str | None = None,
    ) -> str:
        """Helper that mimics TransactionEncoder.build_text without loading model."""
        import re

        def normalize(text: str) -> str:
            text = NOISE_REGEX.sub("", text)
            return re.sub(r"\s+", " ", text).strip()

        parts = []
        if counterparty_name:
            parts.append(normalize(counterparty_name))
        if purpose:
            parts.append(normalize(purpose))
        if reference:
            parts.append(normalize(reference))
        return " | ".join(p for p in parts if p)

    def test_expense_with_counterparty(self) -> None:
        """Test expense transaction with counterparty."""
        text = self._build_text(
            purpose="REWE SAGT DANKE 12345",
            amount=Decimal("-45.67"),
            counterparty_name="REWE",
            reference=None,
        )
        # Amount is intentionally not included in embedding text
        assert text == "REWE | REWE 12345"

    def test_income_with_counterparty(self) -> None:
        """Test income transaction."""
        text = self._build_text(
            purpose="GEHALT JANUAR",
            amount=Decimal("2500.00"),
            counterparty_name="ARBEITGEBER GMBH",
            reference=None,
        )
        # Amount is intentionally not included - format: counterparty | purpose
        assert text == "ARBEITGEBER | GEHALT JANUAR"

    def test_missing_counterparty(self) -> None:
        """Test transaction without counterparty."""
        text = self._build_text(
            purpose="ÜBERWEISUNG",
            amount=Decimal("-100.00"),
            counterparty_name=None,
            reference=None,
        )
        # Only purpose when no counterparty
        assert text == "ÜBERWEISUNG"

    def test_with_reference(self) -> None:
        """Test transaction with reference."""
        text = self._build_text(
            purpose="NETFLIX.COM",
            amount=Decimal("-12.99"),
            counterparty_name="NETFLIX",
            reference="MREF-12345",
        )
        assert text == "NETFLIX | NETFLIX.COM | MREF-12345"

    def test_noise_removal(self) -> None:
        """Test that banking noise patterns are removed."""
        text = self._build_text(
            purpose="REWE SAGT DANKE vom 15.01.2026",
            amount=Decimal("-45.67"),
            counterparty_name="REWE.Berlin.Friedrichsh",
            reference=None,
        )
        # Noise like "SAGT DANKE" and dates should be removed
        assert "SAGT DANKE" not in text
        assert "15.01.2026" not in text


class TestBuildKeywordText:
    """Tests for keyword text construction (used for description matching)."""

    def _build_keyword_text(self, purpose: str, counterparty_name: str | None) -> str:
        """Helper that mimics TransactionEncoder.build_keyword_text."""
        import re

        def normalize(text: str) -> str:
            text = NOISE_REGEX.sub("", text)
            return re.sub(r"\s+", " ", text).strip()

        parts = []
        if counterparty_name:
            n = normalize(counterparty_name)
            if n:
                parts.append(n)
        if purpose:
            n = normalize(purpose)
            if n:
                parts.append(n)
        return " ".join(parts)

    def test_basic_keyword_text(self) -> None:
        """Test keyword text generation."""
        text = self._build_keyword_text(
            purpose="REWE SAGT DANKE 12345",
            counterparty_name="REWE",
        )
        # Keyword text is simpler, without pipe delimiters
        assert "REWE" in text
        assert "SAGT DANKE" not in text  # Noise removed

    def test_keyword_text_without_counterparty(self) -> None:
        """Test keyword text without counterparty."""
        text = self._build_keyword_text(
            purpose="ÜBERWEISUNG MIETE",
            counterparty_name=None,
        )
        assert text == "ÜBERWEISUNG MIETE"


class TestSparseSimilarity:
    """Tests for sparse similarity computation."""

    def test_compute_sparse_similarity(self) -> None:
        """Test sparse vector dot product."""
        from swen_ml.inference.encoding.encoder import TransactionEncoder

        sparse1 = {"rewe": 0.8, "berlin": 0.3, "food": 0.5}
        sparse2 = {"rewe": 0.9, "groceries": 0.4, "food": 0.6}

        sim = TransactionEncoder.compute_sparse_similarity(sparse1, sparse2)

        # Expected: 0.8*0.9 + 0.5*0.6 = 0.72 + 0.30 = 1.02
        assert abs(sim - 1.02) < 0.01

    def test_sparse_similarity_no_overlap(self) -> None:
        """Test sparse similarity with no common tokens."""
        from swen_ml.inference.encoding.encoder import TransactionEncoder

        sparse1 = {"rewe": 0.8, "berlin": 0.3}
        sparse2 = {"aldi": 0.9, "munich": 0.4}

        sim = TransactionEncoder.compute_sparse_similarity(sparse1, sparse2)
        assert sim == 0.0
