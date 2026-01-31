"""Evaluation pipeline runner.

This module provides flexible evaluation utilities that use pipeline
components directly, allowing fine-grained control over what gets tested.

Unlike the production ClassificationOrchestrator, these functions allow:
- Running individual pipeline tiers
- Testing with/without preprocessing
- Custom configurations for experiments
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Literal
from uuid import uuid4

import pandas as pd
from swen_ml_contracts import AccountOption, TransactionInput

from swen_ml.evaluation.metrics import EvaluationMetrics, compute_metrics
from swen_ml.inference import (
    AnchorClassifier,
    ClassificationResult,
    ExampleClassifier,
    NoiseModel,
    PipelineContext,
    TextCleaner,
    TransactionContext,
    build_results,
)
from swen_ml.inference.classification.context import EmbeddingStore

if TYPE_CHECKING:
    from swen_ml.inference._models import Encoder
    from swen_ml.inference.classification.enrichment import KeywordPort, SearXNGAdapter

# Evaluation-specific tier control
ClassificationTier = Literal["preprocessing", "example", "enrichment", "anchor"]
TIER_ORDER: list[ClassificationTier] = [
    "preprocessing",
    "example",
    "enrichment",
    "anchor",
]


@dataclass
class EvaluationResult:
    """Result from an evaluation run."""

    scenario: str
    metrics: EvaluationMetrics
    classifications: list[ClassificationResult]


def load_evaluation_data(
    data_dir: Path,
) -> tuple[list[TransactionInput], list[AccountOption], list[str]]:
    """Load evaluation dataset from CSV files."""
    accounts_df = pd.read_csv(data_dir / "accounts.csv")
    transactions_df = pd.read_csv(data_dir / "transactions.csv")

    # Convert accounts to AccountOption
    accounts = [
        AccountOption(
            account_id=uuid4(),  # Generate dummy IDs for evaluation
            account_number=str(row["number"]),
            name=str(row["name"]),
            account_type=str(row["type"]),
            description=str(row.get("description", "")),
        )
        for _, row in accounts_df.iterrows()
    ]

    # Convert transactions to TransactionInput
    transactions = []
    for _, row in transactions_df.iterrows():
        counterparty = row.get("counterparty")
        has_counterparty = counterparty is not None and str(counterparty) != "nan"
        counterparty_name = str(counterparty) if has_counterparty else None

        purpose_val = row.get("purpose")
        has_purpose = purpose_val is not None and str(purpose_val) != "nan"
        purpose = str(purpose_val) if has_purpose else ""

        transactions.append(
            TransactionInput(
                transaction_id=uuid4(),
                booking_date=date.today(),  # Dummy date for evaluation
                counterparty_name=counterparty_name,
                counterparty_iban=None,
                purpose=purpose,
                amount=Decimal(str(row["amount"])),
            )
        )

    # Expected accounts - convert column to list of strings
    expected_col = transactions_df["expected_account"].astype(int).astype(str).tolist()
    expected: list[str] = expected_col

    return transactions, accounts, expected


def create_pipeline_context(
    encoder: Encoder,
    accounts: list[AccountOption],
    keyword_adapter: KeywordPort | None = None,
    searxng_adapter: SearXNGAdapter | None = None,
    noise_model: NoiseModel | None = None,
    example_store: EmbeddingStore | None = None,
    anchor_store: EmbeddingStore | None = None,
    confidence_threshold: float = 0.85,
) -> PipelineContext:
    """Create a pipeline context for evaluation.

    Args:
        encoder: Embedding model
        accounts: Available accounts
        keyword_adapter: Optional keyword adapter
        searxng_adapter: Optional search adapter
        noise_model: Optional noise model (defaults to empty)
        example_store: Optional EmbeddingStore (defaults to empty)
        anchor_store: Optional EmbeddingStore (defaults to empty)
        confidence_threshold: Classification confidence threshold

    Returns:
        PipelineContext configured for evaluation
    """
    return PipelineContext(
        encoder=encoder,
        noise_model=noise_model or NoiseModel(),
        example_store=example_store or EmbeddingStore.empty(),
        anchor_store=anchor_store or EmbeddingStore.empty(),
        keyword_adapter=keyword_adapter,
        searxng_adapter=searxng_adapter,
        confidence_threshold=confidence_threshold,
    )


async def run_classification_pipeline(
    transactions: list[TransactionInput],
    accounts: list[AccountOption],
    pipeline_ctx: PipelineContext,
    max_tier: ClassificationTier = "anchor",
    skip_preprocessing: bool = False,
) -> list[ClassificationResult]:
    """Run the classification pipeline with fine-grained control.

    This is an evaluation-focused version that allows:
    - Skipping preprocessing to test raw embeddings
    - Stopping at any tier
    - Custom pipeline contexts

    Args:
        transactions: Transactions to classify
        accounts: Available accounts
        pipeline_ctx: Pipeline context with models and stores
        max_tier: Maximum tier to run
        skip_preprocessing: Skip text cleaning and pattern matching

    Returns:
        List of ClassificationResult
    """
    max_tier_idx = TIER_ORDER.index(max_tier)

    # Initialize contexts
    contexts = [TransactionContext.from_input(txn) for txn in transactions]

    # === TIER 1: Preprocessing (optional) ===
    if not skip_preprocessing:
        text_cleaner = TextCleaner(pipeline_ctx)
        text_cleaner.process_batch(contexts)

    if max_tier_idx < TIER_ORDER.index("example"):
        return build_results(contexts)

    # === TIER 2: Example classifier ===
    example_classifier = ExampleClassifier(pipeline_ctx)
    await example_classifier.classify_batch(contexts)

    if max_tier_idx < TIER_ORDER.index("enrichment"):
        return build_results(contexts)

    # Early exit if all resolved
    if all(c.resolved for c in contexts):
        return build_results(contexts)

    # === TIER 3: Enrichment ===
    from swen_ml.inference.classification.enrichment import EnrichmentService

    enrichment_service = EnrichmentService(pipeline_ctx)
    await enrichment_service.enrich_batch(contexts)

    if max_tier_idx < TIER_ORDER.index("anchor"):
        return build_results(contexts)

    # === TIER 4: Anchor classifier ===
    _ = [ctx for ctx in contexts if not ctx.resolved]
    anchor_classifier = AnchorClassifier(pipeline_ctx)
    await anchor_classifier.classify_batch(contexts)

    return build_results(contexts)


def run_cold_start(
    transactions: list[TransactionInput],
    accounts: list[AccountOption],
    expected: list[str],
    encoder: Encoder,
    max_tier: ClassificationTier = "anchor",
    keyword_adapter: KeywordPort | None = None,
    searxng_adapter: SearXNGAdapter | None = None,
    skip_preprocessing: bool = False,
) -> EvaluationResult:
    """Evaluate cold start scenario (no user examples).

    Args:
        transactions: Transactions to classify
        accounts: Available accounts
        expected: Expected account numbers
        encoder: Encoder model
        max_tier: Maximum classification tier to run
        keyword_adapter: Optional keyword adapter
        searxng_adapter: Optional search adapter
        skip_preprocessing: Skip text cleaning and pattern matching

    Returns:
        EvaluationResult with metrics and classifications
    """
    pipeline_ctx = create_pipeline_context(
        encoder=encoder,
        accounts=accounts,
        keyword_adapter=keyword_adapter,
        searxng_adapter=searxng_adapter,
    )

    classifications = asyncio.run(
        run_classification_pipeline(
            transactions=transactions,
            accounts=accounts,
            pipeline_ctx=pipeline_ctx,
            max_tier=max_tier,
            skip_preprocessing=skip_preprocessing,
        )
    )

    metrics = compute_metrics(classifications, expected)

    scenario = f"cold_start_{max_tier}"
    if skip_preprocessing:
        scenario += "_no_preprocess"

    return EvaluationResult(
        scenario=scenario,
        metrics=metrics,
        classifications=classifications,
    )


def run_with_examples(
    transactions: list[TransactionInput],
    accounts: list[AccountOption],
    expected: list[str],
    encoder: Encoder,
    n_folds: int = 5,
    max_tier: ClassificationTier = "anchor",
    keyword_adapter: KeywordPort | None = None,
    searxng_adapter: SearXNGAdapter | None = None,
) -> list[EvaluationResult]:
    """Evaluate with k-fold cross-validation using examples.

    Args:
        transactions: Transactions to classify
        accounts: Available accounts
        expected: Expected account numbers
        encoder: Encoder model
        n_folds: Number of cross-validation folds
        max_tier: Maximum classification tier to run
        keyword_adapter: Optional keyword adapter
        searxng_adapter: Optional search adapter

    Returns:
        List of EvaluationResult, one per fold
    """
    results = []
    n = len(transactions)

    for fold in range(n_folds):
        # Simple fold split
        fold_size = n // n_folds
        test_start = fold * fold_size
        test_end = test_start + fold_size if fold < n_folds - 1 else n

        test_indices = set(range(test_start, test_end))
        train_indices = [i for i in range(n) if i not in test_indices]

        test_txns = [transactions[i] for i in range(n) if i in test_indices]
        test_expected = [expected[i] for i in range(n) if i in test_indices]

        # TODO: Store training examples for this fold
        # For now, run without examples (same as cold start per fold)
        _ = train_indices  # Will be used when example storage is implemented

        pipeline_ctx = create_pipeline_context(
            encoder=encoder,
            accounts=accounts,
            keyword_adapter=keyword_adapter,
            searxng_adapter=searxng_adapter,
        )

        classifications = asyncio.run(
            run_classification_pipeline(
                transactions=test_txns,
                accounts=accounts,
                pipeline_ctx=pipeline_ctx,
                max_tier=max_tier,
            )
        )

        metrics = compute_metrics(classifications, test_expected)
        results.append(
            EvaluationResult(
                scenario=f"cv_fold_{fold}",
                metrics=metrics,
                classifications=classifications,
            )
        )

    return results


def aggregate_cv_results(results: list[EvaluationResult]) -> EvaluationMetrics:
    """Aggregate cross-validation results into a single metrics object."""
    total = sum(r.metrics.total for r in results)
    correct = sum(r.metrics.correct for r in results)
    fallback = sum(r.metrics.fallback_count for r in results)

    aggregated = EvaluationMetrics(
        total=total,
        correct=correct,
        fallback_count=fallback,
    )

    return aggregated
