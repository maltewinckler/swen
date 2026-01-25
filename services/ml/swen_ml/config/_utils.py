import os
from pathlib import Path


def _find_project_root() -> Path:
    """Find the project root directory."""
    current = Path(__file__).resolve().parent

    for parent in [current, *current.parents]:
        if (parent / ".git").is_dir():
            return parent
        if parent == Path("/app"):
            return parent

    return Path(__file__).resolve().parents[4]


def _get_config_dir() -> Path:
    """Get the config directory path (for fints_institute.csv, etc.)."""
    return _find_project_root() / "config"


def resolve_env_file_path() -> Path | None:
    """Resolve the .env file path.

    Priority:
    1. SWEN_ENV_FILE env var (full path)
    2. config/.env.dev (local development)
    3. config/.env (production)
    """
    env_file_path = os.environ.get("SWEN_ENV_FILE")
    if env_file_path:
        path = Path(env_file_path)
        if not path.is_absolute():
            path = _find_project_root() / path
        if path.exists():
            return path

    config_dir = _get_config_dir()
    dev_env = config_dir / ".env.dev"
    if dev_env.exists():
        return dev_env

    prod_env = config_dir / ".env"
    if prod_env.exists():
        return prod_env

    return None
