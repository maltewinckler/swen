"""SWEN CLI application using Typer.

This module provides command-line utilities for SWEN backend,
including secret generation for deployment configuration.
"""

import secrets

import typer
from cryptography.fernet import Fernet
from rich.console import Console

app = typer.Typer(
    name="swen",
    help="SWEN - Secure Wallet & Expense Navigator CLI",
    no_args_is_help=True,
)
console = Console()


# Create secrets subcommand group
secrets_app = typer.Typer(
    name="secrets",
    help="Secret generation utilities",
    no_args_is_help=True,
)
app.add_typer(secrets_app)


@secrets_app.command("generate")
def generate_secrets() -> None:
    """Generate secure secrets for SWEN configuration.

    Generates three required secrets:
    - ENCRYPTION_KEY: Fernet key for encrypting stored credentials
    - JWT_SECRET_KEY: Secret for signing JWT authentication tokens
    - POSTGRES_PASSWORD: Database password

    Copy the output to your .env file.
    """
    console.print("\n[bold green]SWEN Secret Generation[/bold green]")
    console.print("=" * 60)
    console.print(
        "\nGenerated secrets for your [bold].env[/bold] configuration file:\n"
    )

    # Generate Fernet encryption key
    encryption_key = Fernet.generate_key().decode()
    console.print(f"[cyan]ENCRYPTION_KEY[/cyan]={encryption_key}")

    # Generate JWT secret (64 bytes = 128 hex chars for strong HS256)
    jwt_secret = secrets.token_urlsafe(64)
    console.print(f"[cyan]JWT_SECRET_KEY[/cyan]={jwt_secret}")

    # Generate database password (32 bytes = strong random password)
    db_password = secrets.token_urlsafe(32)
    console.print(f"[cyan]POSTGRES_PASSWORD[/cyan]={db_password}")

    console.print("\n" + "=" * 60)
    console.print(
        "[yellow]⚠  Keep these secrets secure and never commit them "
        "to version control![/yellow]"
    )
    console.print(
        "[dim]Copy the above values to your config/.env (Docker) or "
        "config/.env.dev (local) file.[/dim]\n"
    )


def cli() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    cli()
