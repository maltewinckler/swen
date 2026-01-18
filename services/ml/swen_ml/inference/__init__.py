"""Inference module - encoding and classification."""

from .encoder import TransactionEncoder
from .similarity_classifier import SimilarityClassifier

__all__ = ["TransactionEncoder", "SimilarityClassifier"]
