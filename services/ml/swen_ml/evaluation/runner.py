"""Evaluation pipeline runner."""

import asyncio
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pandas as pd
from swen_ml_contracts import AccountOption, Classification, TransactionInput

from swen_ml.evaluation.metrics import EvaluationMetrics, compute_metrics
from swen_ml.models.encoder import Encoder
from swen_ml.models.nli import NLIClassifier
from swen_ml.pipeline.orchestrator import classify_batch


@dataclass
class EvaluationResult:
    """Result from an evaluation run."""

    scenario: str
    metrics: EvaluationMetrics
    classifications: list[Classification]


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


def run_cold_start(
    transactions: list[TransactionInput],
    accounts: list[AccountOption],
    expected: list[str],
    encoder: Encoder,
    nli: NLIClassifier,
) -> EvaluationResult:
    """Evaluate cold start scenario (no user examples)."""
    # Use a dummy user ID that has no stored data
    dummy_user_id = uuid4()

    classifications = asyncio.run(
        classify_batch(
            transactions=transactions,
            accounts=accounts,
            user_id=dummy_user_id,
            encoder=encoder,
            nli=nli,
        )
    )

    metrics = compute_metrics(classifications, expected)

    return EvaluationResult(
        scenario="cold_start",
        metrics=metrics,
        classifications=classifications,
    )


def run_with_examples(
    transactions: list[TransactionInput],
    accounts: list[AccountOption],
    expected: list[str],
    encoder: Encoder,
    nli: NLIClassifier,
    n_folds: int = 5,
) -> list[EvaluationResult]:
    """Evaluate with k-fold cross-validation using examples."""
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

        dummy_user_id = uuid4()
        classifications = asyncio.run(
            classify_batch(
                transactions=test_txns,
                accounts=accounts,
                user_id=dummy_user_id,
                encoder=encoder,
                nli=nli,
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
