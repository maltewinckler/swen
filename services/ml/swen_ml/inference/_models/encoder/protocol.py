"""Encoder protocol definition."""

from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray


@runtime_checkable
class Encoder(Protocol):
    """Protocol for text embedding encoders.

    Implementations can use different backends (SentenceTransformers, HuggingFace, etc.)
    but must provide a consistent interface for encoding text to embeddings.
    """

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        ...

    @property
    def model_name(self) -> str:
        """Return the model identifier."""
        ...

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
        ...

    def warmup(self) -> None:
        """Perform warmup inference to initialize model caches.

        This is optional but recommended for production to avoid
        cold start latency on first real request.
        """
        ...
