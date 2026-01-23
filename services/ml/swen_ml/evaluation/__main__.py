"""Evaluation CLI for swen_ml."""

from pathlib import Path

import typer
from rich.console import Console
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
from swen_ml.models.encoder import Encoder
from swen_ml.models.nli import NLIClassifier

app = typer.Typer(
    name="swen-ml-eval",
    help="Evaluation tools for SWEN ML transaction classification.",
    no_args_is_help=True,
)
console = Console()

# Default data directory relative to the services/ml directory
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_EVAL_DATA = _PROJECT_ROOT / "data" / "examples" / "evaluation"


def _load_models() -> tuple[Encoder, NLIClassifier]:
    """Load encoder and NLI models."""
    settings = get_settings()

    console.print("[dim]Loading embedding model...[/dim]")
    encoder = Encoder.load(settings.embedding_model)

    console.print("[dim]Loading NLI model...[/dim]")
    nli_pipe = pipeline(
        "zero-shot-classification",
        model=settings.nli_model,
        device="cpu",
    )
    nli = NLIClassifier(nli_pipe)

    return encoder, nli


@app.command()
def cold_start() -> None:
    """Evaluate cold start performance (no user examples)."""
    if not _DEFAULT_EVAL_DATA.exists():
        console.print(
            f"[red]Error: Data directory not found: {_DEFAULT_EVAL_DATA}[/red]"
        )
        raise typer.Exit(1)

    console.print("[bold]Cold Start Evaluation[/bold]")
    console.print(f"Data: {_DEFAULT_EVAL_DATA}\n")

    # Load data and models
    transactions, accounts, expected = load_evaluation_data(_DEFAULT_EVAL_DATA)
    encoder, nli = _load_models()

    console.print(
        f"[dim]Loaded {len(transactions)} transactions, "
        f"{len(accounts)} accounts[/dim]\n"
    )

    # Run evaluation
    console.print("[dim]Running classification...[/dim]")
    result = run_cold_start(transactions, accounts, expected, encoder, nli)

    # Display results
    _print_summary(result.metrics)
    _print_tier_breakdown(result.metrics)
    _print_category_breakdown(result.metrics, accounts)


@app.command()
def cross_validate(
    n_folds: int = typer.Option(5, "--folds", "-k", help="Number of CV folds"),
) -> None:
    """Run k-fold cross-validation with example learning."""
    if not _DEFAULT_EVAL_DATA.exists():
        console.print(f"[red]Error: Data not found: {_DEFAULT_EVAL_DATA}[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]{n_folds}-Fold Cross-Validation[/bold]")
    console.print(f"Data: {_DEFAULT_EVAL_DATA}\n")

    # Load data and models
    transactions, accounts, expected = load_evaluation_data(_DEFAULT_EVAL_DATA)
    encoder, nli = _load_models()

    console.print(
        f"[dim]Loaded {len(transactions)} transactions, "
        f"{len(accounts)} accounts[/dim]\n"
    )

    # Run CV
    console.print("[dim]Running cross-validation...[/dim]")
    fold_results = run_with_examples(
        transactions, accounts, expected, encoder, nli, n_folds=n_folds
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
    cold_result = run_cold_start(transactions, accounts, expected, encoder, nli)
    _print_summary(cold_result.metrics)
    console.print()

    # Cross-validation
    console.print(f"[bold cyan]── {n_folds}-Fold Cross-Validation ──[/bold cyan]")
    fold_results = run_with_examples(
        transactions, accounts, expected, encoder, nli, n_folds=n_folds
    )
    aggregated = aggregate_cv_results(fold_results)
    console.print(f"Accuracy: {aggregated.accuracy:.1%}")
    console.print(f"Fallback Rate: {aggregated.fallback_rate:.1%}")
    console.print()

    # Thresholds
    console.print("[bold cyan]── Threshold Check ──[/bold cyan]")
    _check_thresholds(cold_result.metrics, aggregated)


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


if __name__ == "__main__":
    app()
