"""Encoder module for text embeddings.

This module provides a pluggable encoder architecture supporting multiple backends:
- SentenceTransformers (default, recommended)
- HuggingFace Transformers (for experimenting with models like ModernBERT)

Usage:
    from swen_ml.inference._models import create_encoder, Encoder

    encoder = create_encoder(settings)
    embeddings = encoder.encode(["text1", "text2"])
"""

from .factory import create_encoder
from .huggingface import HuggingFaceEncoder
from .protocol import Encoder
from .sentence_transformer import SentenceTransformerEncoder

__all__ = [
    "Encoder",
    "HuggingFaceEncoder",
    "SentenceTransformerEncoder",
    "create_encoder",
]
