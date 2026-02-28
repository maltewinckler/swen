"""Interactive .env setup wizard for SWEN (`swen setup`)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import typer
from cryptography.fernet import Fernet
from rich.console import Console
from rich.panel import Panel

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_config_dir() -> Path:
    """Walk up from this file until we find (or can create) config/."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "config").is_dir():
            return parent / "config"
        if (parent / ".git").is_dir():
            return parent / "config"
        if parent == Path("/app"):
            return parent / "config"
    return Path.cwd() / "config"


def _bool_str(value: bool) -> str:
    return "true" if value else "false"


def _section(title: str) -> list[str]:
    bar = "=" * 77
    return ["", f"# {bar}", f"# {title}", f"# {bar}"]


def _choice_prompt(prompt: str, default: str = "1") -> str:
    """Prompt for a 1/2 choice, re-asking until valid."""
    value = typer.prompt(prompt, default=default)
    while value not in ("1", "2"):
        console.print("[red]Please enter 1 or 2.[/red]")
        value = typer.prompt(prompt, default=default)
    return value


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------


def _step_environment() -> bool:
    """Step 1: ask for environment type. Returns True for production."""
    console.print("[bold]Step 1 / 4 — Environment[/bold]")
    console.print("  [cyan]1[/cyan]  Production  — Docker  →  [dim]config/.env[/dim]")
    console.print(
        "  [cyan]2[/cyan]  Development — bare-metal / Makefile"
        "  →  [dim]config/.env.dev[/dim]"
    )
    console.print()
    choice = _choice_prompt("Select environment [1/2]")
    is_prod = choice == "1"
    label = "Production (Docker)" if is_prod else "Development (bare-metal)"
    console.print(f"  → [green]{label}[/green]\n")
    return is_prod


def _step_registration() -> str:
    """Step 2: ask for registration mode. Returns 'admin_only' or 'open'."""
    console.print("[bold]Step 2 / 4 — Registration Mode[/bold]")
    console.print(
        "  [cyan]1[/cyan]  admin_only  — only admins can create users"
        "  [dim](recommended)[/dim]"
    )
    console.print("  [cyan]2[/cyan]  open        — anyone with the URL can register")
    console.print()
    choice = _choice_prompt("Select registration mode [1/2]")
    mode = "admin_only" if choice == "1" else "open"
    console.print(f"  → [green]{mode}[/green]\n")
    return mode


@dataclass
class SmtpConfig:
    """Collected SMTP settings."""

    enabled: bool
    host: str
    port: int
    user: str
    password: str
    from_email: str
    from_name: str
    use_tls: bool
    starttls: bool
    frontend_base_url: str


def _step_smtp(is_prod: bool) -> SmtpConfig:
    """Step 3: optional SMTP configuration."""
    console.print("[bold]Step 3 / 4 — SMTP (Password Reset Emails)[/bold]")
    enabled = typer.confirm(
        "Configure SMTP for password-reset emails?",
        default=False,
    )
    console.print()

    cfg = SmtpConfig(
        enabled=enabled,
        host="",
        port=587,
        user="",
        password="",
        from_email="",
        from_name="SWEN",
        use_tls=True,
        starttls=True,
        frontend_base_url="" if is_prod else "http://localhost:3000",
    )

    if enabled:
        cfg.host = typer.prompt("  SMTP host")
        cfg.port = int(typer.prompt("  SMTP port", default="587"))
        cfg.user = typer.prompt("  SMTP username")
        cfg.password = typer.prompt("  SMTP password", hide_input=True)
        cfg.from_email = typer.prompt("  From address")
        cfg.from_name = typer.prompt("  From display name", default="SWEN")
        cfg.use_tls = typer.confirm("  Use TLS?", default=True)
        cfg.starttls = typer.confirm("  Use STARTTLS?", default=True)
        console.print()
        console.print(
            "  [dim]FRONTEND_BASE_URL is used to build the password-reset"
            " link included in reset emails.[/dim]"
        )
        default_url = "http://localhost:3000" if not is_prod else ""
        cfg.frontend_base_url = typer.prompt(
            "  Frontend base URL (where users reach the app, no trailing slash)\n"
            "  e.g. https://swen.example.com or http://192.168.1.10:3000",
            default=default_url,
        )
        console.print()

    return cfg


@dataclass
class GeneratedSecrets:
    """Auto-generated cryptographic secrets."""

    encryption_key: str
    jwt_secret_key: str
    postgres_password: str


def _step_secrets() -> GeneratedSecrets:
    """Step 4: generate all secrets."""
    console.print("[bold]Step 4 / 4 — Generating secrets...[/bold]")
    sec = GeneratedSecrets(
        encryption_key=Fernet.generate_key().decode(),
        jwt_secret_key=secrets.token_urlsafe(64),
        postgres_password=secrets.token_urlsafe(32),
    )
    console.print("  [green]✓[/green] ENCRYPTION_KEY  (Fernet)")
    console.print("  [green]✓[/green] JWT_SECRET_KEY  (64-byte urlsafe)")
    console.print("  [green]✓[/green] POSTGRES_PASSWORD  (32-byte urlsafe)")
    console.print()
    return sec


# ---------------------------------------------------------------------------
# File builder
# ---------------------------------------------------------------------------


def _build_content(
    is_prod: bool,
    registration_mode: str,
    smtp: SmtpConfig,
    sec: GeneratedSecrets,
) -> str:
    """Assemble the full .env file content."""
    env_label = "Production (Docker)" if is_prod else "Development (bare-metal)"
    postgres_host = "postgres" if is_prod else "localhost"
    ml_url = "http://ml:8100" if is_prod else "http://localhost:8100"
    searxng_url = "http://searxng:8080" if is_prod else "http://localhost:8888"
    debug = _bool_str(not is_prod)
    log_level = "INFO" if is_prod else "DEBUG"
    today = date.today().isoformat()

    lines: list[str] = [
        f"# SWEN Configuration — generated by `swen setup` on {today}",
        f"# Environment: {env_label}",
        "#",
        "# ⚠  Keep this file secret — never commit it to version control!",
    ]

    lines += _section("Application")
    lines += [
        "APP_NAME=SWEN",
        f"DEBUG={debug}",
        "",
        "# DEBUG, INFO, WARNING, ERROR, CRITICAL",
        f"LOG_LEVEL={log_level}",
    ]

    lines += _section("Database (PostgreSQL)")
    lines += [
        f"POSTGRES_HOST={postgres_host}",
        "POSTGRES_PORT=5432",
        "POSTGRES_USER=postgres",
        f"POSTGRES_PASSWORD={sec.postgres_password}",
    ]

    lines += _section("Security")
    lines += [
        f"ENCRYPTION_KEY={sec.encryption_key}",
        f"JWT_SECRET_KEY={sec.jwt_secret_key}",
    ]

    lines += _section("API Server")
    lines += [
        "API_HOST=0.0.0.0",
        "API_PORT=8000",
        f"API_DEBUG={debug}",
        "",
        "# CORS: comma-separated allowed origins (no wildcards with cookies!)",
        "# Add your production domain here if different from localhost",
        "API_CORS_ORIGINS=http://localhost,http://localhost:3000,http://localhost:5173",
        "",
        "# JWT token expiration",
        "JWT_ACCESS_TOKEN_EXPIRE_HOURS=1",
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS=7",
        "",
        "# Set API_COOKIE_SECURE=true once you serve SWEN over HTTPS",
        "API_COOKIE_SECURE=false",
        "API_COOKIE_SAMESITE=lax",
        "",
        "# Set to true when behind a reverse proxy (Caddy, nginx, etc.)",
        "API_TRUST_PROXY_HEADERS=false",
    ]

    lines += _section("User Registration")
    lines += [
        '# "open" = anyone can register',
        '# "admin_only" = only admins can create users',
        "# Note: the first registered user automatically becomes admin",
        f"REGISTRATION_MODE={registration_mode}",
    ]

    lines += _section("SMTP (Password Reset Emails)")
    lines += [
        f"SMTP_ENABLED={_bool_str(smtp.enabled)}",
        f"SMTP_HOST={smtp.host}",
        f"SMTP_PORT={smtp.port}",
        f"SMTP_USER={smtp.user}",
        f"SMTP_PASSWORD={smtp.password}",
        f"SMTP_FROM_EMAIL={smtp.from_email}",
        f"SMTP_FROM_NAME={smtp.from_name}",
        f"SMTP_USE_TLS={_bool_str(smtp.use_tls)}",
        f"SMTP_STARTTLS={_bool_str(smtp.starttls)}",
        "",
        "# Frontend URL for password-reset links (no trailing slash)",
        f"FRONTEND_BASE_URL={smtp.frontend_base_url}",
    ]

    lines += _section("ML Service (Transaction Classification)")
    lines += [
        "ML_SERVICE_ENABLED=true",
        f"ML_SERVICE_URL={ml_url}",
        "ML_SERVICE_TIMEOUT=10.0",
    ]

    lines += _section("ML Service (Internal Configuration)")
    lines += [
        f"SWEN_ML_ENRICHMENT_SEARXNG_URL={searxng_url}",
        "SWEN_ML_ENCODER_BACKEND=sentence-transformers",
        "SWEN_ML_ENCODER_MODEL=paraphrase-multilingual-MiniLM-L12-v2",
        "SWEN_ML_DEVICE=cpu",
        "SWEN_ML_LOG_LEVEL=INFO",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def setup_command() -> None:
    """Interactively create a complete SWEN .env configuration file."""
    console.print(
        Panel.fit(
            "[bold cyan]SWEN Configuration Setup[/bold cyan]\n"
            "[dim]This wizard generates a complete .env file"
            " for your deployment.[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    is_prod = _step_environment()
    registration_mode = _step_registration()
    smtp = _step_smtp(is_prod)
    sec = _step_secrets()

    config_dir = _find_config_dir()
    output_file = config_dir / (".env" if is_prod else ".env.dev")

    if output_file.exists():
        overwrite = typer.confirm(
            f"  ⚠  {output_file} already exists. Overwrite?",
            default=False,
        )
        if not overwrite:
            console.print("[yellow]Aborted — no file was written.[/yellow]")
            raise typer.Exit(0)
        console.print()

    config_dir.mkdir(parents=True, exist_ok=True)
    output_file.write_text(_build_content(is_prod, registration_mode, smtp, sec))

    prod_tip = (
        "\n[dim]Once behind HTTPS / a reverse proxy, also set:\n"
        "  API_COOKIE_SECURE=true\n"
        "  API_TRUST_PROXY_HEADERS=true[/dim]"
        if is_prod
        else ""
    )
    warning_msg = (
        "[yellow]⚠  Keep this file private —"
        " never commit it to version control![/yellow]"
    )
    console.print(
        Panel.fit(
            f"[bold green]✓  Written to {output_file}[/bold green]\n\n"
            + warning_msg
            + prod_tip,
            border_style="green",
        )
    )
