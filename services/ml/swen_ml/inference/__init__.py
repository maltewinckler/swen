"""Unified inference module.

This module provides the main entry point for all ML inference:
- Classification: determining counter-accounts for transactions
- Merchant extraction: extracting merchant names
- Recurring detection: identifying recurring transaction patterns

Orchestrators (for API layer):
- ClassificationOrchestrator: Coordinates full classification pipeline
- MerchantOrchestrator: Stateless merchant extraction
- RecurringOrchestrator: Stateless recurring detection

Pipeline Components (for evaluation & testing):
- TextCleaner, PatternMatcher: Preprocessing
- ExampleClassifier, AnchorClassifier: Classification
- EnrichmentService: Online enrichment
- TransactionContext, PipelineContext: Data flow
- build_results: Convert contexts to results
"""

from __future__ import annotations

# Classification - Orchestrator
# Classification - Components (for evaluation)
from .classification import (
    AnchorClassifier,
    ClassificationOrchestrator,
    ClassificationResult,
    EmbeddingStore,
    ExampleClassifier,
    NoiseModel,
    PatternMatcher,
    PipelineContext,
    TextCleaner,
    TransactionContext,
    build_results,
)

# Merchant extraction
from .merchant_extraction import extract_merchant
from .merchant_extraction.orchestrator import MerchantOrchestrator, MerchantResult

# Recurring detection
from .recurring_detection import RecurringInfo, RecurringPattern, detect_recurring
from .recurring_detection.orchestrator import RecurringOrchestrator, RecurringResult

# Shared infrastructure
from .shared import SharedInfrastructure

__all__ = [
    # Orchestrators (API layer)
    "ClassificationOrchestrator",
    "MerchantOrchestrator",
    "RecurringOrchestrator",
    "SharedInfrastructure",
    # Classification components (evaluation)
    "TextCleaner",
    "PatternMatcher",
    "NoiseModel",
    "ExampleClassifier",
    "AnchorClassifier",
    "build_results",
    # Classification types
    "ClassificationResult",
    "EmbeddingStore",
    "PipelineContext",
    "TransactionContext",
    # Merchant
    "extract_merchant",
    "MerchantResult",
    # Recurring
    "detect_recurring",
    "RecurringInfo",
    "RecurringResult",
    "RecurringPattern",
]
