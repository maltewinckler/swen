"""Transaction text encoding using sentence transformers."""

import logging
import re
from decimal import Decimal
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Banking noise to strip from text
NOISE_PATTERNS = [
    r"\bSAGT DANKE\b",
    r"\bVIELEN DANK\b",
    r"\bDANKE\b",
    r"\bVISA Debitkartenumsatz\b",
    r"\bEC Kartenzahlung\b",
    r"\bLastschrift\b",
    r"\bDauerauftrag\b",
    r"\bKartenzahlung\b",
    r"\bSepa[-\s]?Lastschrift\b",
    r"\bvom \d{2}\.\d{2}\.\d{4}\b",
    r"\bvom \d{2}\.\d{2}\.\d{2}\b",
    r"\b\d{10,}\b",  # long reference numbers
    r"\bGmbH\b",
    r"\bAG\b",
    r"\bKG\b",
    r"\be\.V\.\b",
]
NOISE_REGEX = re.compile("|".join(NOISE_PATTERNS), re.IGNORECASE)


class TransactionEncoder:
    """Encodes transaction text into embeddings."""

    def __init__(self, model_name: str, cache_folder: Path | None = None):
        logger.info("Loading model: %s", model_name)
        cache_path = str(cache_folder) if cache_folder else None
        self.model = SentenceTransformer(model_name, cache_folder=cache_path)
        self.model_name = model_name

        dim = self.model.get_sentence_embedding_dimension()
        if dim is None:
            raise ValueError(f"Model {model_name} does not provide embedding dimension")
        self.embedding_dim: int = dim

        logger.info("Model loaded (dim=%d)", self.embedding_dim)

    def _normalize(self, text: str) -> str:
        """Remove banking noise and collapse whitespace."""
        text = NOISE_REGEX.sub("", text)
        return re.sub(r"\s+", " ", text).strip()

    def build_text(
        self,
        purpose: str,
        amount: Decimal,  # kept for API compat, unused
        counterparty_name: str | None,
        reference: str | None = None,
    ) -> str:
        """
        Full text for example storage and matching.

        Format: "counterparty | purpose | reference" (normalized)
        """
        parts = []
        if counterparty_name:
            parts.append(self._normalize(counterparty_name))
        if purpose:
            parts.append(self._normalize(purpose))
        if reference:
            parts.append(self._normalize(reference))
        return " | ".join(p for p in parts if p)

    def build_keyword_text(self, purpose: str, counterparty_name: str | None) -> str:
        """
        Simplified text for description matching (cold start).

        Format: "counterparty purpose" (normalized, no delimiters)
        """
        parts = []
        if counterparty_name:
            n = self._normalize(counterparty_name)
            if n:
                parts.append(n)
        if purpose:
            n = self._normalize(purpose)
            if n:
                parts.append(n)
        return " ".join(parts)

    def encode(self, text: str) -> NDArray[np.float32]:
        """Encode text to normalized embedding."""
        return self.model.encode(text, normalize_embeddings=True, convert_to_numpy=True)

    def encode_batch(self, texts: list[str]) -> NDArray[np.float32]:
        """Encode texts to normalized embeddings."""
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self.embedding_dim)
        return self.model.encode(
            texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False
        )
