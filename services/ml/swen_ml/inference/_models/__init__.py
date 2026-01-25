"""ML model wrappers (private module).

This module provides model abstractions for:
- Encoder: Text embeddings (multiple backends supported)
- NLI: Natural Language Inference for zero-shot classification
"""

from .encoder import (
    Encoder,
    HuggingFaceEncoder,
    SentenceTransformerEncoder,
    create_encoder,
)
from .nli import NLIClassifier

__all__ = [
    "Encoder",
    "HuggingFaceEncoder",
    "NLIClassifier",
    "SentenceTransformerEncoder",
    "create_encoder",
]
