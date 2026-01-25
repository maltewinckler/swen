"""Zero-shot NLI model wrapper."""

from typing import Any

import numpy as np
from numpy.typing import NDArray
from transformers import pipeline


class NLIClassifier:
    """Wrapper around HuggingFace zero-shot classification pipeline."""

    def __init__(self, pipe: Any):
        self._pipe = pipe

    @classmethod
    def load(cls, model_name: str, device: str = "cpu") -> "NLIClassifier":
        """Load NLI classifier from model name."""
        pipe = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=device,
        )
        return cls(pipe)

    def classify(
        self,
        texts: list[str],
        labels: list[str],
        batch_size: int = 32,
    ) -> NDArray[np.float32]:
        """Classify texts against candidate labels.

        Args:
            texts: List of texts to classify.
            labels: Candidate labels (account names).
            batch_size: Batch size for inference.

        Returns:
            Array of shape (N, num_labels) with entailment scores.
        """
        results = self._pipe(
            texts,
            labels,
            multi_label=False,
            batch_size=batch_size,
        )

        # Handle single result
        if not isinstance(results, list):
            results = [results]

        # Build score matrix
        scores = np.zeros((len(texts), len(labels)), dtype=np.float32)
        for i, result in enumerate(results):
            for j, label in enumerate(labels):
                idx = result["labels"].index(label)
                scores[i, j] = result["scores"][idx]

        return scores

    def warmup(self, labels: list[str]) -> None:
        """Warmup the model with a dummy classification."""
        _ = self.classify(["warmup"], labels)
