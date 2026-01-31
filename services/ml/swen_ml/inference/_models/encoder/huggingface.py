"""HuggingFace Transformers-based encoder implementation."""

from __future__ import annotations

import logging
from typing import Any, Literal

import numpy as np
import torch
from numpy.typing import NDArray
from transformers import AutoModel, AutoTokenizer, PreTrainedModel, PreTrainedTokenizer

logger = logging.getLogger(__name__)

PoolingStrategy = Literal["mean", "cls", "max"]


class HuggingFaceEncoder:
    """Encoder using raw HuggingFace Transformers.

    This provides more flexibility for experimenting with models that
    aren't available as SentenceTransformers, like ModernBERT.

    Implements configurable pooling strategies:
    - mean: Average over all tokens (weighted by attention mask)
    - cls: Use the [CLS] token embedding
    - max: Max pooling over tokens
    """

    def __init__(
        self,
        model: PreTrainedModel,
        tokenizer: PreTrainedTokenizer,
        model_name: str,
        pooling: PoolingStrategy = "mean",
        normalize: bool = True,
        max_length: int = 512,
    ):
        self._model: PreTrainedModel = model
        self._tokenizer: Any = tokenizer  # Tokenizers have complex callable types
        self._model_name = model_name
        self._pooling = pooling
        self._normalize = normalize
        self._max_length = max_length
        self._dimension: int | None = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"

        # Move model to device
        self._model.to(self._device)  # type: ignore[arg-type]
        self._model.eval()

    @classmethod
    def load(
        cls,
        model_name: str,
        pooling: PoolingStrategy = "mean",
        normalize: bool = True,
        max_length: int = 512,
    ) -> HuggingFaceEncoder:
        """Load a HuggingFace model by name.

        Parameters
        ----------
        model_name
            Model identifier from HuggingFace Hub.
            Examples: "answerdotai/ModernBERT-base",
                      "bert-base-multilingual-cased"
        pooling
            Pooling strategy: "mean", "cls", or "max"
        normalize
            Whether to L2-normalize embeddings (recommended for cosine similarity)
        max_length
            Maximum sequence length for tokenization
        """
        logger.info(
            "Loading HuggingFace model: %s (pooling=%s, normalize=%s)",
            model_name,
            pooling,
            normalize,
        )
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        return cls(
            model=model,
            tokenizer=tokenizer,
            model_name=model_name,
            pooling=pooling,
            normalize=normalize,
            max_length=max_length,
        )

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        if self._dimension is None:
            hidden_size = getattr(self._model.config, "hidden_size", None)
            if hidden_size is None:
                msg = "Model config does not have hidden_size attribute"
                raise ValueError(msg)
            self._dimension = int(hidden_size)
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

        # Tokenize
        encoded = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self._max_length,
            return_tensors="pt",
        )

        # Move to device
        encoded = {k: v.to(self._device) for k, v in encoded.items()}

        # Forward pass
        with torch.no_grad():
            outputs = self._model(**encoded)

        # Get embeddings based on pooling strategy
        embeddings = self._pool(
            outputs.last_hidden_state,
            encoded["attention_mask"],
        )

        # Normalize if requested
        if self._normalize:
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

        return embeddings.cpu().numpy().astype(np.float32)

    def _pool(
        self,
        hidden_states: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:
        """Apply pooling strategy to hidden states.

        Parameters
        ----------
        hidden_states
            Shape: (batch_size, seq_len, hidden_size)
        attention_mask
            Shape: (batch_size, seq_len)

        Returns
        -------
        torch.Tensor
            Pooled embeddings with shape (batch_size, hidden_size)
        """
        if self._pooling == "cls":
            return hidden_states[:, 0]

        if self._pooling == "max":
            # Mask padding tokens with -inf before max
            mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size())
            hidden_states[mask_expanded == 0] = float("-inf")
            return torch.max(hidden_states, dim=1).values

        # Default: mean pooling
        mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size())
        sum_embeddings = torch.sum(hidden_states * mask_expanded, dim=1)
        sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)
        return sum_embeddings / sum_mask

    def warmup(self) -> None:
        """Perform warmup inference."""
        _ = self.encode(["warmup"])
        logger.debug("HuggingFace encoder warmed up (device=%s)", self._device)
