"""SentenceTransformer-based encoder implementation."""

from __future__ import annotations

import logging

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class SentenceTransformerEncoder:
    """Encoder using the sentence-transformers library.

    This is the recommended default as it handles tokenization, pooling,
    and normalization automatically for models designed for semantic similarity.
    """

    def __init__(self, model: SentenceTransformer, model_name: str):
        self._model = model
        self._model_name = model_name
        self._dimension: int | None = None

    @classmethod
    def load(cls, model_name: str) -> SentenceTransformerEncoder:
        """Load a SentenceTransformer model by name.

        Parameters
        ----------
        model_name
            Model identifier from HuggingFace Hub or local path.
            Examples: "paraphrase-multilingual-MiniLM-L12-v2",
                      "sentence-transformers/all-MiniLM-L6-v2"
        """
        logger.info("Loading SentenceTransformer model: %s", model_name)
        model = SentenceTransformer(model_name)
        return cls(model, model_name)

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        if self._dimension is None:
            dim = self._model.get_sentence_embedding_dimension()
            if dim is None:
                msg = "Could not determine embedding dimension from model."
                raise ValueError(msg)
            self._dimension = dim
        return self._dimension

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        return self._model_name

    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        """Encode texts to embeddings.

        Parameters
        ----------
        texts
            List of texts to encode.

        Returns
        -------
        NDArray[np.float32]
            Embeddings with shape (n_texts, dimension).
        """
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)

        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)

    def warmup(self) -> None:
        """Perform warmup inference."""
        _ = self.encode(["warmup"])
        logger.debug("SentenceTransformer encoder warmed up")
