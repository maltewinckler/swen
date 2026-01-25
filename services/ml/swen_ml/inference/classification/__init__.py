"""Classification pipeline module.

Exports:
- Orchestrator: ClassificationOrchestrator for production API use
- Components: Individual pipeline components for evaluation/testing
- Context: TransactionContext, PipelineContext for data flow
- Result: ClassificationResult for output
- Utilities: build_results for converting contexts to results
"""

from .classifiers import AnchorClassifier, ExampleClassifier
from .context import EmbeddingStore, PipelineContext, TransactionContext
from .orchestrator import ClassificationOrchestrator, build_results
from .preprocessing import NoiseModel, PatternMatcher, TextCleaner
from .result import ClassificationResult

__all__ = [
    # Orchestrator
    "ClassificationOrchestrator",
    # Components (for evaluation)
    "TextCleaner",
    "PatternMatcher",
    "NoiseModel",
    "ExampleClassifier",
    "AnchorClassifier",
    # Context
    "EmbeddingStore",
    "PipelineContext",
    "TransactionContext",
    # Result
    "ClassificationResult",
    # Utilities
    "build_results",
]
