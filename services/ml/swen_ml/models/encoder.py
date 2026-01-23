"""Sentence embedding encoder."""

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer


class Encoder:
    """Wrapper around SentenceTransformer for batch encoding."""

    def __init__(self, model: SentenceTransformer):
        self._model = model

    @classmethod
    def load(cls, model_name: str) -> "Encoder":
        """Load encoder from model name."""
        model = SentenceTransformer(model_name)
        return cls(model)

    def encode(
        self,
        texts: list[str],
        batch_size: int = 64,
        show_progress: bool = False,
    ) -> NDArray[np.float32]:
        """Encode texts to embeddings.

        Args:
            texts: List of texts to encode.
            batch_size: Batch size for encoding.
            show_progress: Show progress bar.

        Returns:
            Array of shape (N, embedding_dim).
        """
        return self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )

    def encode_single(self, text: str) -> NDArray[np.float32]:
        """Encode a single text."""
        return self.encode([text])[0]

    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        dim = self._model.get_sentence_embedding_dimension()
        if dim is None:
            raise ValueError("Model does not have a fixed embedding dimension")
        return dim

    def warmup(self) -> None:
        """Warmup the model with a dummy encoding."""
        _ = self.encode(["warmup"])
