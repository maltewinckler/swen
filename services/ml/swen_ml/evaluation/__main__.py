"""Evaluation CLI for swen_ml."""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from transformers import pipeline

from swen_ml.config.settings import get_settings
from swen_ml.evaluation.metrics import category_accuracy, tier_accuracy
from swen_ml.evaluation.runner import (
    aggregate_cv_results,
    load_evaluation_data,
    run_cold_start,
    run_with_examples,
)
from swen_ml.inference import MerchantExtractor, RecurringDetector
from swen_ml.inference._models import Encoder, NLIClassifier, create_encoder
from swen_ml.inference.classification.enrichment import (
    SearXNGAdapter,
    extract_enrichment_text,
)
from swen_ml.inference.classification.preprocessing import NoiseModel
from swen_ml.inference.classification.preprocessing.text_cleaner import (
    clean_counterparty,
)
from swen_ml.inference.merchant_extraction import extract_merchant

# Note: Noise model loading from database is not supported in CLI evaluation.
# Use an empty NoiseModel for evaluation purposes.

app = typer.Typer(
    name="swen-ml-eval",
    help="Evaluation tools for SWEN ML transaction classification.",
    no_args_is_help=True,
)
console = Console()

# NLI model for evaluation (not used in production)
_NLI_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"

# Default data directory relative to the services/ml directory
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_EVAL_DATA = _PROJECT_ROOT / "data" / "examples" / "evaluation"


def _load_models() -> tuple[Encoder, NLIClassifier]:
    """Load encoder and NLI models."""
    settings = get_settings()

    console.print(
        f"[dim]Loading encoder: {settings.encoder_backend}/{settings.encoder_model}[/dim]"
    )
    encoder = create_encoder(settings)

    console.print(f"[dim]Loading NLI model: {_NLI_MODEL}[/dim]")
    nli_pipe = pipeline(
        "zero-shot-classification",
        model=_NLI_MODEL,
        device="cpu",
    )
    nli = NLIClassifier(nli_pipe)

    return encoder, nli


@app.command()
def cold_start(
    max_tier: str = typer.Option(
        "anchor",
        "--max-tier",
        "-t",
        help="Maximum tier: preprocessing, example, enrichment, anchor",
    ),
) -> None:
    """Evaluate cold start performance (no user examples)."""
    if not _DEFAULT_EVAL_DATA.exists():
        console.print(
            f"[red]Error: Data directory not found: {_DEFAULT_EVAL_DATA}[/red]"
        )
        raise typer.Exit(1)

    # Validate tier
    valid_tiers = ["preprocessing", "example", "enrichment", "anchor"]
    if max_tier not in valid_tiers:
        console.print(
            f"[red]Invalid tier: {max_tier}. Must be one of {valid_tiers}[/red]"
        )
        raise typer.Exit(1)

    console.print(f"[bold]Cold Start Evaluation (max_tier={max_tier})[/bold]")
    console.print(f"Data: {_DEFAULT_EVAL_DATA}\n")

    # Load data and models
    transactions, accounts, expected = load_evaluation_data(_DEFAULT_EVAL_DATA)
    encoder, _ = _load_models()

    console.print(
        f"[dim]Loaded {len(transactions)} transactions, "
        f"{len(accounts)} accounts[/dim]\n"
    )

    # Run evaluation
    console.print("[dim]Running classification...[/dim]")
    result = run_cold_start(
        transactions,
        accounts,
        expected,
        encoder,
        max_tier=max_tier,  # type: ignore[arg-type]
    )

    # Display results
    _print_summary(result.metrics)
    _print_tier_breakdown(result.metrics)
    _print_category_breakdown(result.metrics, accounts)


@app.command()
def cross_validate(
    n_folds: int = typer.Option(5, "--folds", "-k", help="Number of CV folds"),
    max_tier: str = typer.Option(
        "anchor",
        "--max-tier",
        "-t",
        help="Maximum tier: preprocessing, example, enrichment, anchor",
    ),
) -> None:
    """Run k-fold cross-validation with example learning."""
    if not _DEFAULT_EVAL_DATA.exists():
        console.print(f"[red]Error: Data not found: {_DEFAULT_EVAL_DATA}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]{n_folds}-Fold Cross-Validation (max_tier={max_tier})[/bold]")
    console.print(f"Data: {_DEFAULT_EVAL_DATA}\n")

    # Load data and models
    transactions, accounts, expected = load_evaluation_data(_DEFAULT_EVAL_DATA)
    encoder, _ = _load_models()

    console.print(
        f"[dim]Loaded {len(transactions)} transactions, "
        f"{len(accounts)} accounts[/dim]\n"
    )

    # Run CV
    console.print("[dim]Running cross-validation...[/dim]")
    fold_results = run_with_examples(
        transactions,
        accounts,
        expected,
        encoder,
        n_folds=n_folds,
        max_tier=max_tier,  # type: ignore[arg-type]
    )

    # Per-fold results
    table = Table(title="Per-Fold Results")
    table.add_column("Fold", style="cyan")
    table.add_column("Accuracy", justify="right")
    table.add_column("Fallback Rate", justify="right")

    for result in fold_results:
        table.add_row(
            result.scenario,
            f"{result.metrics.accuracy:.1%}",
            f"{result.metrics.fallback_rate:.1%}",
        )

    console.print(table)
    console.print()

    # Aggregated
    aggregated = aggregate_cv_results(fold_results)
    console.print(f"[bold]Aggregated: {aggregated.accuracy:.1%} accuracy[/bold]")


@app.command()
def full(
    n_folds: int = typer.Option(5, "--folds", "-k", help="Number of CV folds"),
) -> None:
    """Run full evaluation suite (cold start + cross-validation)."""
    if not _DEFAULT_EVAL_DATA.exists():
        console.print(
            f"[red]Error: Data directory not found: {_DEFAULT_EVAL_DATA}[/red]"
        )
        raise typer.Exit(1)

    console.print("[bold blue]═══ Full Evaluation Suite ═══[/bold blue]\n")

    # Load data and models once
    transactions, accounts, expected = load_evaluation_data(_DEFAULT_EVAL_DATA)
    encoder, nli = _load_models()

    console.print(
        f"[dim]Loaded {len(transactions)} transactions, "
        f"{len(accounts)} accounts[/dim]\n"
    )

    # Cold start
    console.print("[bold cyan]── Cold Start ──[/bold cyan]")
    cold_result = run_cold_start(transactions, accounts, expected, encoder)
    _print_summary(cold_result.metrics)
    console.print()

    # Cross-validation
    console.print(f"[bold cyan]── {n_folds}-Fold Cross-Validation ──[/bold cyan]")
    fold_results = run_with_examples(
        transactions, accounts, expected, encoder, n_folds=n_folds
    )
    aggregated = aggregate_cv_results(fold_results)
    console.print(f"Accuracy: {aggregated.accuracy:.1%}")
    console.print(f"Fallback Rate: {aggregated.fallback_rate:.1%}")
    console.print()

    # Thresholds
    console.print("[bold cyan]── Threshold Check ──[/bold cyan]")
    _check_thresholds(cold_result.metrics, aggregated)


@app.command("merchants")
def extract_merchants_cmd() -> None:
    """Extract merchant names from transactions."""
    if not _DEFAULT_EVAL_DATA.exists():
        console.print(f"[red]Error: Data not found: {_DEFAULT_EVAL_DATA}[/red]")
        raise typer.Exit(1)

    console.print("[bold]Merchant Extraction[/bold]")
    console.print(f"Data: {_DEFAULT_EVAL_DATA}\n")

    # Load data
    transactions, _, _ = load_evaluation_data(_DEFAULT_EVAL_DATA)

    # Extract merchants
    merchant_extractor = MerchantExtractor()
    results = merchant_extractor.extract(transactions)

    # Display results
    table = Table(title="Merchant Extraction Results")
    table.add_column("Counterparty", style="dim", max_width=40)
    table.add_column("Merchant", style="cyan")

    n_extracted = 0
    for r in results:
        if r.merchant:
            n_extracted += 1
        table.add_row(
            r.counterparty[:40] if r.counterparty else "-",
            r.merchant or "[dim]-[/dim]",
        )

    console.print(table)
    console.print(f"\n[bold]Extracted: {n_extracted}/{len(results)}[/bold]")


@app.command("recurring")
def detect_recurring_cmd() -> None:
    """Detect recurring transaction patterns."""
    if not _DEFAULT_EVAL_DATA.exists():
        console.print(f"[red]Error: Data not found: {_DEFAULT_EVAL_DATA}[/red]")
        raise typer.Exit(1)

    console.print("[bold]Recurring Pattern Detection[/bold]")
    console.print(f"Data: {_DEFAULT_EVAL_DATA}\n")

    # Load data
    transactions, _, _ = load_evaluation_data(_DEFAULT_EVAL_DATA)

    # Detect recurring
    recurring_detector = RecurringDetector()
    results = recurring_detector.detect(transactions)

    # Display results
    recurring_results = [r for r in results if r.is_recurring]

    if not recurring_results:
        console.print("[yellow]No recurring patterns detected.[/yellow]")
        return

    table = Table(title="Recurring Patterns")
    table.add_column("Pattern", style="cyan")
    table.add_column("Occurrences", justify="right")
    table.add_column("Transaction IDs", style="dim")

    # Group by pattern
    from collections import defaultdict

    patterns: dict[str, list] = defaultdict(list)
    for r in recurring_results:
        if r.pattern:
            patterns[r.pattern].append(r)

    for pattern, items in patterns.items():
        table.add_row(
            pattern,
            str(len(items)),
            f"{len(items)} transactions",
        )

    console.print(table)
    console.print(f"\n[bold]Recurring: {len(recurring_results)}/{len(results)}[/bold]")


def _print_summary(metrics) -> None:
    """Print summary metrics."""
    console.print(f"Accuracy: [bold]{metrics.accuracy:.1%}[/bold]")
    console.print(f"High-Conf Accuracy: {metrics.high_confidence_accuracy:.1%}")
    console.print(f"Fallback Rate: {metrics.fallback_rate:.1%}")


def _print_tier_breakdown(metrics) -> None:
    """Print per-tier breakdown."""
    table = Table(title="Per-Tier Breakdown")
    table.add_column("Tier", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Accuracy", justify="right")

    for tier_name in ["pattern", "example", "anchor", "nli", "fallback"]:
        tier_data = metrics.by_tier.get(tier_name, {"correct": 0, "total": 0})
        if tier_data["total"] > 0:
            acc = tier_accuracy(metrics, tier_name)
            table.add_row(tier_name, str(tier_data["total"]), f"{acc:.1%}")

    console.print(table)


def _print_category_breakdown(metrics, accounts) -> None:
    """Print per-category breakdown."""
    table = Table(title="Per-Category Breakdown")
    table.add_column("Account", style="cyan")
    table.add_column("Name")
    table.add_column("Count", justify="right")
    table.add_column("Accuracy", justify="right")

    account_names = {a.account_number: a.name for a in accounts}

    for account_num, cat_data in sorted(metrics.by_category.items()):
        if cat_data["total"] > 0:
            acc = category_accuracy(metrics, account_num)
            name = account_names.get(account_num, "Unknown")
            table.add_row(account_num, name, str(cat_data["total"]), f"{acc:.1%}")

    console.print(table)


def _check_thresholds(cold_metrics, warm_metrics) -> None:
    """Check if metrics meet thresholds."""
    thresholds = [
        ("Cold Start Accuracy", cold_metrics.accuracy, 0.85),
        ("Warm Accuracy", warm_metrics.accuracy, 0.92),
        ("Fallback Rate", cold_metrics.fallback_rate, 0.10),
        ("High-Conf Accuracy", cold_metrics.high_confidence_accuracy, 0.95),
    ]

    all_passed = True
    for name, value, target in thresholds:
        # For fallback rate, lower is better
        if name == "Fallback Rate":
            passed = value <= target
            symbol = "≤"
        else:
            passed = value >= target
            symbol = "≥"

        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f"{status} {name}: {value:.1%} ({symbol} {target:.0%} target)")

        if not passed:
            all_passed = False

    console.print()
    if all_passed:
        console.print("[bold green]All thresholds met![/bold green]")
    else:
        console.print("[bold red]Some thresholds not met.[/bold red]")


# -----------------------------------------------------------------------------
# Similarity Tool
# -----------------------------------------------------------------------------


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    dot = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))


@app.command()
def similarity(
    text1: str = typer.Argument(..., help="First transaction text"),
    text2: str = typer.Argument(..., help="Second transaction text"),
    user_id: str | None = typer.Option(
        None,
        "--user",
        "-u",
        help="User ID to load noise model for text cleaning",
    ),
    no_clean: bool = typer.Option(
        False,
        "--no-clean",
        help="Skip noise model cleaning (use raw text)",
    ),
) -> None:
    """Compute embedding similarity between two transaction texts.

    Examples:
        # Basic similarity
        uv run python -m swen_ml.evaluation similarity "REWE SAGT DANKE" "EDEKA Filiale"

        # With user's noise model
        uv run python -m swen_ml.evaluation similarity "REWE" "EDEKA" -u <user-id>

        # Raw text (no cleaning)
        uv run python -m swen_ml.evaluation similarity "text1" "text2" --no-clean
    """
    settings = get_settings()

    # Load encoder
    console.print(
        f"[dim]Loading encoder: {settings.encoder_backend}/{settings.encoder_model}[/dim]"
    )
    encoder = create_encoder(settings)

    # Prepare texts
    clean1, clean2 = text1, text2

    if not no_clean:
        # Note: Database-based noise model not supported in CLI evaluation
        # For evaluation purposes, we use raw text (no noise cleaning)
        if user_id:
            console.print(
                "[dim]Note: Database noise model not supported in CLI. Using raw text.[/dim]"
            )

    # Compute embeddings
    embeddings = encoder.encode([clean1, clean2])
    emb1, emb2 = embeddings[0], embeddings[1]

    # Compute similarity
    sim = _cosine_similarity(emb1, emb2)

    # Display results
    console.print()
    console.print(Panel.fit("[bold]Embedding Similarity[/bold]"))

    table = Table(show_header=True, header_style="bold")
    table.add_column("", style="dim")
    table.add_column("Text 1")
    table.add_column("Text 2")

    table.add_row("Raw", f"[cyan]{text1}[/cyan]", f"[cyan]{text2}[/cyan]")

    if clean1 != text1 or clean2 != text2:
        table.add_row("Cleaned", f"[green]{clean1}[/green]", f"[green]{clean2}[/green]")

    console.print(table)
    console.print()

    # Similarity with color coding
    if sim >= 0.8:
        color = "green"
        label = "High"
    elif sim >= 0.5:
        color = "yellow"
        label = "Medium"
    else:
        color = "red"
        label = "Low"

    console.print(
        f"Cosine Similarity: [{color}][bold]{sim:.4f}[/bold][/{color}] ({label})"
    )
    console.print(f"[dim]Embedding dimension: {encoder.dimension}[/dim]")


@app.command()
def embed(
    texts: list[str] = typer.Argument(..., help="Texts to embed"),
    show_vector: bool = typer.Option(
        False, "--vector", "-v", help="Show first 10 embedding values"
    ),
) -> None:
    """Embed one or more texts and show pairwise similarities.

    Examples:
        uv run python -m swen_ml.evaluation embed "REWE" "EDEKA" "Amazon"
    """
    settings = get_settings()

    console.print(
        f"[dim]Loading encoder: {settings.encoder_backend}/{settings.encoder_model}[/dim]"
    )
    encoder = create_encoder(settings)

    # Compute embeddings
    embeddings = encoder.encode(list(texts))

    console.print()
    console.print(Panel.fit(f"[bold]Embeddings for {len(texts)} texts[/bold]"))

    # Show texts and optionally vectors
    for i, (text, emb) in enumerate(zip(texts, embeddings)):
        console.print(f"[cyan]{i + 1}.[/cyan] {text}")
        if show_vector:
            vec_str = ", ".join(f"{v:.4f}" for v in emb[:10])
            console.print(f"   [dim][{vec_str}, ...][/dim]")

    # Pairwise similarity matrix
    if len(texts) > 1:
        console.print()
        table = Table(title="Pairwise Cosine Similarity")
        table.add_column("", style="dim")
        for i in range(len(texts)):
            table.add_column(f"T{i + 1}", justify="center")

        for i in range(len(texts)):
            row = [f"T{i + 1}"]
            for j in range(len(texts)):
                sim = _cosine_similarity(embeddings[i], embeddings[j])
                if i == j:
                    row.append("[dim]1.0[/dim]")
                elif sim >= 0.8:
                    row.append(f"[green]{sim:.3f}[/green]")
                elif sim >= 0.5:
                    row.append(f"[yellow]{sim:.3f}[/yellow]")
                else:
                    row.append(f"[red]{sim:.3f}[/red]")
            table.add_row(*row)

        console.print(table)

    console.print(f"\n[dim]Embedding dimension: {encoder.dimension}[/dim]")


@app.command()
def neighbors(
    k: int = typer.Option(3, "--k", "-k", help="Number of nearest neighbors"),
    csv_path: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to transactions CSV (default: evaluation data)",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="Limit to first N transactions",
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all transactions (default: only mismatched accounts)",
    ),
) -> None:
    """Find k nearest neighbor transactions for each transaction in a CSV.

    By default, only shows transactions where neighbors have different
    expected accounts (interesting cases). Use --all to show everything.

    Examples:
        # Find 3 nearest neighbors for each transaction
        uv run python -m swen_ml.evaluation neighbors

        # Find 5 nearest neighbors, limit to first 20 transactions
        uv run python -m swen_ml.evaluation neighbors -k 5 -n 20

        # Use custom CSV file
        uv run python -m swen_ml.evaluation neighbors -f my_transactions.csv
    """
    settings = get_settings()

    # Determine CSV path
    if csv_path is None:
        csv_path = _DEFAULT_EVAL_DATA / "transactions.csv"

    if not csv_path.exists():
        console.print(f"[red]Error: File not found: {csv_path}[/red]")
        raise typer.Exit(1)

    # Load transactions
    console.print(f"[dim]Loading transactions from: {csv_path}[/dim]")
    df = pd.read_csv(csv_path)

    if limit:
        df = df.head(limit)

    n_txns = len(df)
    console.print(f"[dim]Loaded {n_txns} transactions[/dim]")

    # Build text for each transaction
    texts = []
    for _, row in df.iterrows():
        cp_val = row.get("counterparty")
        purpose_val = row.get("purpose")
        counterparty = (
            str(cp_val) if cp_val is not None and str(cp_val) != "nan" else ""
        )
        purpose = (
            str(purpose_val)
            if purpose_val is not None and str(purpose_val) != "nan"
            else ""
        )
        text = f"{counterparty} {purpose}".strip()
        texts.append(text if text else "(empty)")

    # Load encoder and compute embeddings
    console.print(
        f"[dim]Loading encoder: {settings.encoder_backend}/{settings.encoder_model}[/dim]"
    )
    encoder = create_encoder(settings)

    console.print("[dim]Computing embeddings...[/dim]")
    embeddings = encoder.encode(texts)

    # Compute pairwise similarities
    console.print("[dim]Computing pairwise similarities...[/dim]")
    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1  # Avoid division by zero
    normalized = embeddings / norms
    similarity_matrix = normalized @ normalized.T

    # For each transaction, find k nearest neighbors (excluding self)
    console.print()
    console.print(Panel.fit(f"[bold]{k} Nearest Neighbors per Transaction[/bold]"))

    # Get expected accounts for comparison
    expected_accounts = df["expected_account"].astype(str).tolist()

    displayed = 0
    for i in range(n_txns):
        # Get similarities, excluding self
        sims = similarity_matrix[i].copy()
        sims[i] = -1  # Exclude self

        # Get top k indices
        top_k_idx = np.argsort(sims)[-k:][::-1]
        top_k_sims = sims[top_k_idx]

        # Check if any neighbor has different account
        has_mismatch = any(
            expected_accounts[j] != expected_accounts[i] for j in top_k_idx
        )

        # Skip if no mismatch and not showing all
        if not show_all and not has_mismatch:
            continue

        displayed += 1

        # Display source transaction
        src_text = texts[i][:60] + "..." if len(texts[i]) > 60 else texts[i]
        src_account = expected_accounts[i]
        console.print(
            f"\n[bold cyan]#{i + 1}[/bold cyan] [cyan]{src_text}[/cyan] "
            f"[dim](account: {src_account})[/dim]"
        )

        # Display neighbors
        table = Table(show_header=True, header_style="dim", box=None, padding=(0, 1))
        table.add_column("Rank", style="dim", width=4)
        table.add_column("Sim", justify="right", width=6)
        table.add_column("Account", width=8)
        table.add_column("Text")

        for rank, (j, sim) in enumerate(zip(top_k_idx, top_k_sims), 1):
            neighbor_text = texts[j][:50] + "..." if len(texts[j]) > 50 else texts[j]
            neighbor_account = expected_accounts[j]

            # Color code: green if same account, red if different
            if neighbor_account == src_account:
                account_str = f"[green]{neighbor_account}[/green]"
            else:
                account_str = f"[red]{neighbor_account}[/red]"

            # Color code similarity
            if sim >= 0.8:
                sim_str = f"[green]{sim:.3f}[/green]"
            elif sim >= 0.5:
                sim_str = f"[yellow]{sim:.3f}[/yellow]"
            else:
                sim_str = f"[red]{sim:.3f}[/red]"

            table.add_row(str(rank), sim_str, account_str, neighbor_text)

        console.print(table)

    # Summary
    console.print()
    if show_all:
        console.print(f"[dim]Displayed all {displayed} transactions[/dim]")
    else:
        console.print(
            f"[dim]Displayed {displayed}/{n_txns} transactions "
            f"(with neighbor account mismatches)[/dim]"
        )
        console.print("[dim]Use --all to show all transactions[/dim]")


@app.command("anchor-eval")
def anchor_eval(
    top_k: int = typer.Option(3, "--top", "-k", help="Show top K account matches"),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="Limit to first N transactions",
    ),
    show_correct: bool = typer.Option(
        False,
        "--correct",
        "-c",
        help="Also show correctly matched transactions",
    ),
    threshold: float = typer.Option(
        0.55,
        "--threshold",
        "-t",
        help="Similarity threshold for classification",
    ),
) -> None:
    """Evaluate cold-start anchor embedding similarity.

    Computes embedding similarity between all transactions and all account
    descriptions to evaluate how well anchor-based classification works.

    Examples:
        # Run anchor evaluation
        uv run python -m swen_ml.evaluation anchor-eval

        # Show top 5 matches, include correct ones
        uv run python -m swen_ml.evaluation anchor-eval -k 5 --correct

        # Limit to first 30 transactions
        uv run python -m swen_ml.evaluation anchor-eval -n 30
    """
    settings = get_settings()

    # Paths
    txn_path = _DEFAULT_EVAL_DATA / "transactions.csv"
    acc_path = _DEFAULT_EVAL_DATA / "accounts.csv"

    if not txn_path.exists() or not acc_path.exists():
        console.print(
            f"[red]Error: Evaluation data not found in {_DEFAULT_EVAL_DATA}[/red]"
        )
        raise typer.Exit(1)

    # Load data
    console.print("[dim]Loading evaluation data...[/dim]")
    txn_df = pd.read_csv(txn_path)
    acc_df = pd.read_csv(acc_path)

    if limit:
        txn_df = txn_df.head(limit)

    n_txns = len(txn_df)
    n_accs = len(acc_df)
    console.print(f"[dim]Loaded {n_txns} transactions, {n_accs} accounts[/dim]")

    # Build transaction texts
    txn_texts = []
    for _, row in txn_df.iterrows():
        cp_val = row.get("counterparty")
        purpose_val = row.get("purpose")
        counterparty = (
            str(cp_val) if cp_val is not None and str(cp_val) != "nan" else ""
        )
        purpose = (
            str(purpose_val)
            if purpose_val is not None and str(purpose_val) != "nan"
            else ""
        )
        text = f"{counterparty} {purpose}".strip()
        txn_texts.append(text if text else "(empty)")

    expected_accounts = txn_df["expected_account"].astype(str).tolist()

    # Build account texts (name + description)
    acc_texts = []
    acc_numbers = []
    acc_names = []
    for _, row in acc_df.iterrows():
        name_val = row["name"]
        desc_val = row["description"]
        name = str(name_val) if name_val is not None and str(name_val) != "nan" else ""
        desc = str(desc_val) if desc_val is not None and str(desc_val) != "nan" else ""
        acc_texts.append(f"{name} {desc}".strip())
        acc_numbers.append(str(row["number"]))
        acc_names.append(name)

    # Load encoder
    console.print(
        f"[dim]Loading encoder: {settings.encoder_backend}/{settings.encoder_model}[/dim]"
    )
    encoder = create_encoder(settings)

    # Compute embeddings
    console.print("[dim]Computing transaction embeddings...[/dim]")
    txn_embeddings = encoder.encode(txn_texts)

    console.print("[dim]Computing account embeddings...[/dim]")
    acc_embeddings = encoder.encode(acc_texts)

    # Normalize for cosine similarity
    txn_norms = np.linalg.norm(txn_embeddings, axis=1, keepdims=True)
    txn_norms[txn_norms == 0] = 1
    txn_normalized = txn_embeddings / txn_norms

    acc_norms = np.linalg.norm(acc_embeddings, axis=1, keepdims=True)
    acc_norms[acc_norms == 0] = 1
    acc_normalized = acc_embeddings / acc_norms

    # Compute similarity matrix: transactions x accounts
    console.print("[dim]Computing similarities...[/dim]")
    similarity_matrix = txn_normalized @ acc_normalized.T

    # Evaluate
    console.print()
    console.print(Panel.fit("[bold]Anchor Embedding Evaluation (Cold Start)[/bold]"))

    correct = 0
    above_threshold = 0
    errors: list[tuple[int, str, str, float, list[tuple[str, str, float]]]] = []

    for i in range(n_txns):
        sims = similarity_matrix[i]
        top_idx = np.argsort(sims)[-top_k:][::-1]
        top_sims = sims[top_idx]

        predicted_idx = top_idx[0]
        predicted_account = acc_numbers[predicted_idx]
        predicted_sim = top_sims[0]
        expected = expected_accounts[i]

        is_correct = predicted_account == expected
        is_above_threshold = predicted_sim >= threshold

        if is_correct:
            correct += 1
        if is_above_threshold:
            above_threshold += 1

        # Collect top-k for display
        top_matches = [(acc_numbers[j], acc_names[j], float(sims[j])) for j in top_idx]

        if not is_correct:
            errors.append((i, txn_texts[i], expected, predicted_sim, top_matches))
        elif show_correct:
            errors.append((i, txn_texts[i], expected, predicted_sim, top_matches))

    # Summary statistics
    accuracy = correct / n_txns if n_txns > 0 else 0
    threshold_rate = above_threshold / n_txns if n_txns > 0 else 0

    console.print(
        f"[bold]Accuracy:[/bold] {correct}/{n_txns} = [cyan]{accuracy:.1%}[/cyan]"
    )
    console.print(
        f"[bold]Above threshold ({threshold}):[/bold] {above_threshold}/{n_txns} "
        f"= [cyan]{threshold_rate:.1%}[/cyan]"
    )
    console.print()

    # Per-account breakdown
    acc_stats: dict[str, dict[str, int]] = {
        num: {"correct": 0, "total": 0} for num in acc_numbers
    }
    for i, expected in enumerate(expected_accounts):
        if expected in acc_stats:
            acc_stats[expected]["total"] += 1
            predicted_idx = np.argmax(similarity_matrix[i])
            if acc_numbers[predicted_idx] == expected:
                acc_stats[expected]["correct"] += 1

    table = Table(title="Per-Account Accuracy")
    table.add_column("Account", style="cyan")
    table.add_column("Name")
    table.add_column("Correct", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Accuracy", justify="right")

    for num, name in zip(acc_numbers, acc_names):
        stats = acc_stats[num]
        if stats["total"] > 0:
            acc = stats["correct"] / stats["total"]
            if acc >= 0.8:
                acc_str = f"[green]{acc:.0%}[/green]"
            elif acc >= 0.5:
                acc_str = f"[yellow]{acc:.0%}[/yellow]"
            else:
                acc_str = f"[red]{acc:.0%}[/red]"
            table.add_row(
                num, name, str(stats["correct"]), str(stats["total"]), acc_str
            )

    console.print(table)

    # Show errors (or all if --correct)
    if errors:
        console.print()
        label = "Transactions" if show_correct else "Misclassified Transactions"
        console.print(f"[bold]{label}:[/bold]")

        for idx, text, expected, pred_sim, top_matches in errors[:20]:  # Limit display
            text_short = text[:55] + "..." if len(text) > 55 else text
            console.print(f"\n[dim]#{idx + 1}[/dim] [cyan]{text_short}[/cyan]")
            console.print(f"   Expected: [green]{expected}[/green]")

            match_table = Table(show_header=False, box=None, padding=(0, 1))
            match_table.add_column("Rank", width=4, style="dim")
            match_table.add_column("Account", width=6)
            match_table.add_column("Name", width=20)
            match_table.add_column("Sim", width=6, justify="right")

            for rank, (acc_num, acc_name, sim) in enumerate(top_matches, 1):
                if acc_num == expected:
                    acc_str = f"[green]{acc_num}[/green]"
                    name_str = f"[green]{acc_name}[/green]"
                else:
                    acc_str = f"[red]{acc_num}[/red]" if rank == 1 else acc_num
                    name_str = acc_name

                if sim >= threshold:
                    sim_str = f"[green]{sim:.3f}[/green]"
                else:
                    sim_str = f"[dim]{sim:.3f}[/dim]"

                match_table.add_row(str(rank), acc_str, name_str, sim_str)

            console.print(match_table)

        if len(errors) > 20:
            console.print(f"\n[dim]... and {len(errors) - 20} more[/dim]")


# -----------------------------------------------------------------------------
# Embedding Ablation Study
# -----------------------------------------------------------------------------


class TextStrategy:
    """Text preprocessing strategy for ablation studies."""

    def __init__(
        self,
        name: str,
        use_counterparty: bool = True,
        use_purpose: bool = True,
        use_noise_model: bool = False,
        use_merchant: bool = False,
    ):
        self.name = name
        self.use_counterparty = use_counterparty
        self.use_purpose = use_purpose
        self.use_noise_model = use_noise_model
        self.use_merchant = use_merchant

    def build_text(
        self,
        counterparty: str,
        purpose: str,
        merchant: str | None,
        noise_model: NoiseModel | None,
    ) -> str:
        """Build text according to strategy."""
        if self.use_merchant and merchant:
            text = merchant
        else:
            parts = []
            if self.use_counterparty and counterparty:
                parts.append(counterparty)
            if self.use_purpose and purpose:
                parts.append(purpose)
            text = " ".join(parts)

        if self.use_noise_model and noise_model and noise_model.doc_count > 0:
            text = noise_model.clean(text)

        return text.strip() if text else "(empty)"


# Predefined strategies
STRATEGIES = [
    TextStrategy("raw", use_counterparty=True, use_purpose=True, use_noise_model=False),
    TextStrategy(
        "cleaned", use_counterparty=True, use_purpose=True, use_noise_model=True
    ),
    TextStrategy("counterparty_only", use_counterparty=True, use_purpose=False),
    TextStrategy("purpose_only", use_counterparty=False, use_purpose=True),
    TextStrategy(
        "counterparty_cleaned",
        use_counterparty=True,
        use_purpose=False,
        use_noise_model=True,
    ),
    TextStrategy(
        "purpose_cleaned",
        use_counterparty=False,
        use_purpose=True,
        use_noise_model=True,
    ),
]


@app.command("embedding-ablation")
def embedding_ablation(
    threshold: float = typer.Option(
        0.55, "--threshold", "-t", help="Similarity threshold"
    ),
    strategies: list[str] | None = typer.Option(
        None,
        "--strategy",
        "-s",
        help="Strategies to test (default: all). Options: raw, cleaned, etc.",
    ),
) -> None:
    """Compare embedding accuracy across preprocessing strategies.

    Tests anchor embedding similarity WITHOUT pattern matching.
    Shows how different preprocessing affects classification accuracy.

    Examples:
        # Run all strategies
        uv run python -m swen_ml.evaluation embedding-ablation

        # Compare specific strategies
        uv run python -m swen_ml.evaluation embedding-ablation -s raw -s cleaned

        # With different threshold
        uv run python -m swen_ml.evaluation embedding-ablation -t 0.6
    """
    settings = get_settings()

    # Paths
    txn_path = _DEFAULT_EVAL_DATA / "transactions.csv"
    acc_path = _DEFAULT_EVAL_DATA / "accounts.csv"

    if not txn_path.exists() or not acc_path.exists():
        console.print(
            f"[red]Error: Evaluation data not found in {_DEFAULT_EVAL_DATA}[/red]"
        )
        raise typer.Exit(1)

    # Load data
    console.print("[dim]Loading evaluation data...[/dim]")
    txn_df = pd.read_csv(txn_path)
    acc_df = pd.read_csv(acc_path)

    n_txns = len(txn_df)
    n_accs = len(acc_df)
    console.print(f"[dim]Loaded {n_txns} transactions, {n_accs} accounts[/dim]")

    # Extract raw fields
    counterparties = []
    purposes = []
    merchants: list[str | None] = []
    expected_accounts = txn_df["expected_account"].astype(str).tolist()

    for _, row in txn_df.iterrows():
        cp_val = row.get("counterparty")
        purpose_val = row.get("purpose")
        cp = str(cp_val) if cp_val is not None and str(cp_val) != "nan" else ""
        p = (
            str(purpose_val)
            if purpose_val is not None and str(purpose_val) != "nan"
            else ""
        )
        counterparties.append(cp)
        purposes.append(p)
        # Extract merchant from counterparty (simple heuristic)
        merchants.append(extract_merchant(counterparties[-1]))

    # Build noise model from all texts
    console.print("[dim]Building noise model...[/dim]")
    all_texts = [f"{cp} {p}".strip() for cp, p in zip(counterparties, purposes)]
    noise_model = NoiseModel()
    noise_model.observe_batch(all_texts)
    console.print(
        f"[dim]Noise model: {noise_model.doc_count} docs, "
        f"{len(noise_model.get_noise_tokens())} noise tokens[/dim]"
    )

    # Build account texts
    acc_texts = []
    acc_numbers = []
    acc_names = []
    for _, row in acc_df.iterrows():
        name_val = row["name"]
        desc_val = row["description"]
        name = str(name_val) if name_val is not None and str(name_val) != "nan" else ""
        desc = str(desc_val) if desc_val is not None and str(desc_val) != "nan" else ""
        acc_texts.append(f"{name} {desc}".strip())
        acc_numbers.append(str(row["number"]))
        acc_names.append(name)

    # Load encoder
    console.print(
        f"[dim]Loading encoder: {settings.encoder_backend}/{settings.encoder_model}[/dim]"
    )
    encoder = create_encoder(settings)

    # Compute account embeddings (same for all strategies)
    console.print("[dim]Computing account embeddings...[/dim]")
    acc_embeddings = encoder.encode(acc_texts)
    acc_norms = np.linalg.norm(acc_embeddings, axis=1, keepdims=True)
    acc_norms[acc_norms == 0] = 1
    acc_normalized = acc_embeddings / acc_norms

    # Filter strategies
    active_strategies = STRATEGIES
    if strategies:
        active_strategies = [s for s in STRATEGIES if s.name in strategies]
        if not active_strategies:
            opts = [s.name for s in STRATEGIES]
            console.print(f"[red]No valid strategies. Options: {opts}[/red]")
            raise typer.Exit(1)

    # Run each strategy
    results: list[dict] = []

    for strategy in active_strategies:
        console.print(f"[dim]Testing strategy: {strategy.name}...[/dim]")

        # Build texts for this strategy
        txn_texts = [
            strategy.build_text(cp, p, m, noise_model)
            for cp, p, m in zip(counterparties, purposes, merchants)
        ]

        # Compute embeddings
        txn_embeddings = encoder.encode(txn_texts)
        txn_norms = np.linalg.norm(txn_embeddings, axis=1, keepdims=True)
        txn_norms[txn_norms == 0] = 1
        txn_normalized = txn_embeddings / txn_norms

        # Compute similarities
        similarity_matrix = txn_normalized @ acc_normalized.T

        # Evaluate
        correct = 0
        above_threshold = 0
        total_sim = 0.0
        confidences = []

        for i in range(n_txns):
            sims = similarity_matrix[i]
            best_idx = int(np.argmax(sims))
            best_sim = float(sims[best_idx])
            predicted = acc_numbers[best_idx]
            expected = expected_accounts[i]

            if predicted == expected:
                correct += 1
            if best_sim >= threshold:
                above_threshold += 1

            total_sim += best_sim
            confidences.append(best_sim)

        accuracy = correct / n_txns
        threshold_rate = above_threshold / n_txns
        avg_sim = total_sim / n_txns
        sim_std = float(np.std(confidences))

        results.append(
            {
                "strategy": strategy.name,
                "accuracy": accuracy,
                "threshold_rate": threshold_rate,
                "avg_sim": avg_sim,
                "sim_std": sim_std,
                "correct": correct,
                "total": n_txns,
            }
        )

    # Display results
    console.print()
    console.print(
        Panel.fit(
            f"[bold]Embedding Ablation Study[/bold]\n"
            f"[dim]Encoder: {settings.encoder_model} | Threshold: {threshold}[/dim]"
        )
    )

    table = Table(title="Preprocessing Strategy Comparison")
    table.add_column("Strategy", style="cyan")
    table.add_column("Accuracy", justify="right")
    table.add_column("Above Thresh", justify="right")
    table.add_column("Avg Sim", justify="right")
    table.add_column("Sim Std", justify="right")

    # Sort by accuracy descending
    results.sort(key=lambda x: x["accuracy"], reverse=True)
    best_acc = results[0]["accuracy"]

    for r in results:
        # Color code accuracy
        if r["accuracy"] == best_acc:
            acc_str = f"[bold green]{r['accuracy']:.1%}[/bold green]"
        elif r["accuracy"] >= best_acc - 0.05:
            acc_str = f"[green]{r['accuracy']:.1%}[/green]"
        elif r["accuracy"] >= best_acc - 0.15:
            acc_str = f"[yellow]{r['accuracy']:.1%}[/yellow]"
        else:
            acc_str = f"[red]{r['accuracy']:.1%}[/red]"

        table.add_row(
            r["strategy"],
            acc_str,
            f"{r['threshold_rate']:.1%}",
            f"{r['avg_sim']:.3f}",
            f"{r['sim_std']:.3f}",
        )

    console.print(table)

    # Show insights
    console.print()
    console.print("[bold]Insights:[/bold]")

    # Compare raw vs cleaned
    raw_result = next((r for r in results if r["strategy"] == "raw"), None)
    cleaned_result = next((r for r in results if r["strategy"] == "cleaned"), None)

    if raw_result and cleaned_result:
        diff = cleaned_result["accuracy"] - raw_result["accuracy"]
        if diff > 0:
            console.print(
                f"  • Noise cleaning: [green]+{diff:.1%}[/green] accuracy improvement"
            )
        elif diff < 0:
            console.print(
                f"  • Noise cleaning: [red]{diff:.1%}[/red] accuracy (hurts performance)"
            )
        else:
            console.print("  • Noise cleaning: no effect on accuracy")

    # Best strategy
    console.print(f"  • Best strategy: [bold cyan]{results[0]['strategy']}[/bold cyan]")

    # Similarity distribution insight
    avg_std = sum(r["sim_std"] for r in results) / len(results)
    if avg_std < 0.1:
        console.print(
            "  • [yellow]Low similarity variance[/yellow] - embeddings may be anisotropic"
        )


# -----------------------------------------------------------------------------
# Search Enrichment Evaluation
# -----------------------------------------------------------------------------


@app.command("search-eval")
def search_eval(
    searxng_url: str = typer.Option(
        "http://localhost:8888",
        "--url",
        "-u",
        help="SearXNG base URL",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="Limit to first N transactions",
    ),
    threshold: float = typer.Option(
        0.55,
        "--threshold",
        "-t",
        help="Similarity threshold for classification",
    ),
    show_snippets: bool = typer.Option(
        False,
        "--snippets",
        "-s",
        help="Show search result snippets",
    ),
    method: str = typer.Option(
        "embedding",
        "--method",
        "-m",
        help="Classification method: 'embedding' or 'nli'",
    ),
) -> None:
    """Evaluate if search enrichment improves classification.

    Compares classification accuracy with two methods:
    - embedding: Cosine similarity with account embeddings
    - nli: Zero-shot NLI classification

    For each method:
    1. Baseline: counterparty + purpose text
    2. Search-enhanced: baseline + search result snippets

    Requires SearXNG to be running (docker compose up searxng).

    Examples:
        # Embedding-based evaluation (default)
        uv run python -m swen_ml.evaluation search-eval

        # NLI zero-shot evaluation
        uv run python -m swen_ml.evaluation search-eval --method nli

        # Limit to 10 transactions (faster testing)
        uv run python -m swen_ml.evaluation search-eval -n 10 -m nli
    """
    if method not in ("embedding", "nli"):
        console.print(
            f"[red]Error: method must be 'embedding' or 'nli', got '{method}'[/red]"
        )
        raise typer.Exit(1)
    settings = get_settings()

    # Paths
    txn_path = _DEFAULT_EVAL_DATA / "transactions.csv"
    acc_path = _DEFAULT_EVAL_DATA / "accounts.csv"

    if not txn_path.exists() or not acc_path.exists():
        console.print(f"[red]Error: Data not found in {_DEFAULT_EVAL_DATA}[/red]")
        raise typer.Exit(1)

    # Initialize search client
    search_client = SearXNGAdapter(base_url=searxng_url)

    # Test connection
    console.print(f"[dim]Testing SearXNG at {searxng_url}...[/dim]")
    test_results = search_client.search_sync("test")
    if not test_results:
        console.print(
            "[yellow]Warning: SearXNG returned no results for test query[/yellow]"
        )
        console.print(
            "[dim]Make sure SearXNG is running: docker compose up searxng[/dim]"
        )

    # Load data
    console.print("[dim]Loading evaluation data...[/dim]")
    txn_df = pd.read_csv(txn_path)
    acc_df = pd.read_csv(acc_path)

    if limit:
        txn_df = txn_df.head(limit)

    n_txns = len(txn_df)
    console.print(f"[dim]Loaded {n_txns} transactions[/dim]")

    # Extract fields
    counterparties = []
    purposes = []
    expected_accounts = txn_df["expected_account"].astype(str).tolist()

    for _, row in txn_df.iterrows():
        cp_val = row.get("counterparty")
        purpose_val = row.get("purpose")
        cp = str(cp_val) if cp_val is not None and str(cp_val) != "nan" else ""
        p = (
            str(purpose_val)
            if purpose_val is not None and str(purpose_val) != "nan"
            else ""
        )
        counterparties.append(cp)
        purposes.append(p)

    # Build account texts (name + description for semantic matching)
    acc_texts = []
    acc_numbers = []
    acc_names = []
    for _, row in acc_df.iterrows():
        name_val = row["name"]
        desc_val = row.get("description")
        name = str(name_val) if name_val is not None and str(name_val) != "nan" else ""
        desc = str(desc_val) if desc_val is not None and str(desc_val) != "nan" else ""
        # Combine name + description for richer semantic signal
        acc_text = f"{name} {desc}".strip() if desc else name
        acc_texts.append(acc_text)
        acc_numbers.append(str(row["number"]))
        acc_names.append(name)

    # Load models based on method
    use_nli = method == "nli"

    if use_nli:
        console.print(f"[dim]Loading NLI model: {_NLI_MODEL}[/dim]")
        nli = NLIClassifier.load(_NLI_MODEL, device=settings.device)
        # Use full account texts (name + description) as NLI labels for richer context
        # This prevents generic labels like "Abonnements" from matching everything
        nli_labels = acc_texts
        nli.warmup(nli_labels[:3])  # Warmup with a few labels
        encoder = None
        acc_normalized = None
    else:
        console.print(
            f"[dim]Loading encoder: {settings.encoder_backend}/{settings.encoder_model}[/dim]"
        )
        encoder = create_encoder(settings)

        # Compute account embeddings (name + description)
        console.print("[dim]Computing account embeddings (name + description)...[/dim]")
        acc_embeddings = encoder.encode(acc_texts)
        acc_norms = np.linalg.norm(acc_embeddings, axis=1, keepdims=True)
        acc_norms[acc_norms == 0] = 1
        acc_normalized = acc_embeddings / acc_norms
        nli = None

    # Process transactions
    console.print("[dim]Searching and classifying...[/dim]")
    console.print()

    baseline_correct = 0
    enhanced_correct = 0
    search_helped = 0
    search_hurt = 0
    no_results_count = 0

    detailed_results: list[dict] = []

    with console.status("[bold]Processing transactions...") as status:
        for i in range(n_txns):
            cp = counterparties[i]
            purpose = purposes[i]
            expected = expected_accounts[i]

            # Baseline text
            baseline_text = f"{cp} {purpose}".strip()

            # Search for counterparty
            search_query = clean_counterparty(cp) or cp
            status.update(f"[bold]Searching: {search_query[:30]}...")

            search_results = search_client.search_sync(search_query)

            # Build enhanced text using smart extraction
            if search_results:
                snippets = extract_enrichment_text(search_results, max_length=300)
                enhanced_text = f"{baseline_text} {snippets}"
            else:
                snippets = ""
                enhanced_text = baseline_text
                no_results_count += 1

            # Log the enrichment
            console.print(f"\n[dim]#{i + 1}[/dim] [cyan]{search_query[:40]}[/cyan]")
            if snippets:
                console.print(f"    [green]+ {snippets[:80]}...[/green]")
            else:
                console.print("    [yellow](no results)[/yellow]")

            # Rate limit: wait 2 seconds between searches
            time.sleep(2.0)

            # Classify using chosen method
            if use_nli:
                # NLI zero-shot classification using full account descriptions
                assert nli is not None
                scores = nli.classify([baseline_text, enhanced_text], nli_labels)
                baseline_pred_idx = int(np.argmax(scores[0]))
                enhanced_pred_idx = int(np.argmax(scores[1]))
                baseline_sim = float(scores[0, baseline_pred_idx])
                enhanced_sim = float(scores[1, enhanced_pred_idx])
            else:
                # Embedding similarity
                assert encoder is not None
                assert acc_normalized is not None
                texts_to_embed = [baseline_text, enhanced_text]
                embeddings = encoder.encode(texts_to_embed)

                # Normalize
                norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
                norms[norms == 0] = 1
                normalized = embeddings / norms

                # Compute similarities
                baseline_sims = normalized[0] @ acc_normalized.T
                enhanced_sims = normalized[1] @ acc_normalized.T

                baseline_pred_idx = int(np.argmax(baseline_sims))
                enhanced_pred_idx = int(np.argmax(enhanced_sims))
                baseline_sim = float(baseline_sims[baseline_pred_idx])
                enhanced_sim = float(enhanced_sims[enhanced_pred_idx])

            baseline_pred = acc_numbers[baseline_pred_idx]
            enhanced_pred = acc_numbers[enhanced_pred_idx]

            # Track results
            baseline_is_correct = baseline_pred == expected
            enhanced_is_correct = enhanced_pred == expected

            if baseline_is_correct:
                baseline_correct += 1
            if enhanced_is_correct:
                enhanced_correct += 1

            if not baseline_is_correct and enhanced_is_correct:
                search_helped += 1
            if baseline_is_correct and not enhanced_is_correct:
                search_hurt += 1

            detailed_results.append(
                {
                    "idx": i,
                    "counterparty": cp,
                    "expected": expected,
                    "baseline_pred": baseline_pred,
                    "enhanced_pred": enhanced_pred,
                    "baseline_sim": baseline_sim,
                    "enhanced_sim": enhanced_sim,
                    "baseline_correct": baseline_is_correct,
                    "enhanced_correct": enhanced_is_correct,
                    "search_results": len(search_results),
                    "snippets": snippets[:200] if search_results else "",
                }
            )

    # Display results
    console.print()
    method_info = (
        f"NLI: {_NLI_MODEL}"
        if use_nli
        else f"Embedding: {settings.encoder_model}"
    )
    console.print(
        Panel.fit(
            "[bold]Search Enrichment Evaluation[/bold]\n"
            f"[dim]Method: {method_info}[/dim]"
        )
    )

    # Summary table
    baseline_acc = baseline_correct / n_txns
    enhanced_acc = enhanced_correct / n_txns
    diff = enhanced_acc - baseline_acc

    table = Table(title="Accuracy Comparison")
    table.add_column("Method", style="cyan")
    table.add_column("Correct", justify="right")
    table.add_column("Accuracy", justify="right")
    table.add_column("Δ", justify="right")

    table.add_row(
        "Baseline (no search)",
        f"{baseline_correct}/{n_txns}",
        f"{baseline_acc:.1%}",
        "-",
    )

    if diff > 0:
        diff_str = f"[green]+{diff:.1%}[/green]"
    elif diff < 0:
        diff_str = f"[red]{diff:.1%}[/red]"
    else:
        diff_str = "0%"

    table.add_row(
        "Search-enhanced",
        f"{enhanced_correct}/{n_txns}",
        f"{enhanced_acc:.1%}",
        diff_str,
    )

    console.print(table)

    # Impact analysis
    console.print()
    console.print("[bold]Impact Analysis:[/bold]")
    console.print(f"  • Search helped (fixed errors): [green]{search_helped}[/green]")
    console.print(f"  • Search hurt (caused errors): [red]{search_hurt}[/red]")
    console.print(f"  • No search results: {no_results_count}/{n_txns}")

    net_impact = search_helped - search_hurt
    if net_impact > 0:
        console.print(
            f"  • [bold green]Net improvement: +{net_impact} transactions[/bold green]"
        )
    elif net_impact < 0:
        console.print(
            f"  • [bold red]Net regression: {net_impact} transactions[/bold red]"
        )
    else:
        console.print("  • [yellow]No net change[/yellow]")

    # Show detailed cases where search helped or hurt
    if show_snippets or search_helped > 0 or search_hurt > 0:
        console.print()

        # Cases where search helped
        helped_cases = [
            r
            for r in detailed_results
            if not r["baseline_correct"] and r["enhanced_correct"]
        ]
        if helped_cases:
            console.print("[bold green]Cases where search HELPED:[/bold green]")
            for case in helped_cases:
                console.print(
                    f"  #{case['idx'] + 1} [cyan]{case['counterparty'][:40]}[/cyan]"
                )
                console.print(
                    f"      Baseline: [red]{case['baseline_pred']}[/red] → "
                    f"Enhanced: [green]{case['enhanced_pred']}[/green] "
                    f"(expected: {case['expected']})"
                )
                if show_snippets and case["snippets"]:
                    console.print(
                        f"      [dim]Snippets: {case['snippets'][:100]}...[/dim]"
                    )

        # Cases where search hurt
        hurt_cases = [
            r
            for r in detailed_results
            if r["baseline_correct"] and not r["enhanced_correct"]
        ]
        if hurt_cases:
            console.print()
            console.print("[bold red]Cases where search HURT:[/bold red]")
            for case in hurt_cases:
                console.print(
                    f"  #{case['idx'] + 1} [cyan]{case['counterparty'][:40]}[/cyan]"
                )
                console.print(
                    f"      Baseline: [green]{case['baseline_pred']}[/green] → "
                    f"Enhanced: [red]{case['enhanced_pred']}[/red] "
                    f"(expected: {case['expected']})"
                )
                if show_snippets and case["snippets"]:
                    console.print(
                        f"      [dim]Snippets: {case['snippets'][:100]}...[/dim]"
                    )

        # Remaining cases (unchanged - both correct or both wrong)
        unchanged_cases = [
            r
            for r in detailed_results
            if r["baseline_correct"] == r["enhanced_correct"]
        ]
        if unchanged_cases:
            console.print()
            # Split into correct and incorrect
            both_correct = [c for c in unchanged_cases if c["baseline_correct"]]
            both_wrong = [c for c in unchanged_cases if not c["baseline_correct"]]

            if both_correct:
                console.print(
                    f"[bold blue]Unchanged - Both CORRECT ({len(both_correct)}):[/bold blue]"
                )
                for case in both_correct:
                    console.print(
                        f"  #{case['idx'] + 1} [cyan]{case['counterparty'][:40]}[/cyan] "
                        f"→ [green]{case['baseline_pred']}[/green]"
                    )

            if both_wrong:
                console.print()
                console.print(
                    f"[bold yellow]Unchanged - Both WRONG ({len(both_wrong)}):[/bold yellow]"
                )
                for case in both_wrong:
                    console.print(
                        f"  #{case['idx'] + 1} [cyan]{case['counterparty'][:40]}[/cyan]"
                    )
                    console.print(
                        f"      Predicted: [red]{case['baseline_pred']}[/red] "
                        f"(expected: {case['expected']})"
                    )
                    if show_snippets and case["snippets"]:
                        console.print(
                            f"      [dim]Snippets: {case['snippets'][:100]}...[/dim]"
                        )

    # Recommendation
    console.print()
    if diff >= 0.05:
        console.print(
            "[bold green]✓ Recommendation: Search enrichment shows promise! "
            "Consider integrating.[/bold green]"
        )
    elif diff >= 0:
        console.print(
            "[yellow]○ Recommendation: Marginal improvement. "
            "May not be worth the latency.[/yellow]"
        )
    else:
        console.print(
            "[red]✗ Recommendation: Search enrichment hurts accuracy. "
            "Do not integrate.[/red]"
        )


if __name__ == "__main__":
    app()
