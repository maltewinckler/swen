"""FastAPI application factory.

Creates and configures the FastAPI application with all routers,
middleware, and exception handlers.

API Versioning:
    All API endpoints are versioned under /api/v1/ prefix.
    Future breaking changes will be introduced under /api/v2/, etc.
    The health check endpoint remains unversioned at /health.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from swen_config.settings import get_settings


def _configure_logging() -> None:
    """Configure application logging.

    Sets up structured logging for the swen application with:
    - Console output with timestamps and module names
    - Configurable log level for swen modules (from settings)
    - WARNING level for noisy third-party libraries
    """
    settings = get_settings()
    log_level_str = settings.log_level.upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Define log format
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        force=True,  # Override any existing config
    )

    # Set levels for our application
    logging.getLogger("swen").setLevel(log_level)
    logging.getLogger("swen_identity").setLevel(log_level)

    # Quiet down noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("fints").setLevel(logging.WARNING)


# Configure logging on module import (before app creation)
_configure_logging()

# Imports below logging config to ensure all module-level logs are properly formatted
from fastapi import APIRouter, FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from swen.infrastructure.persistence.sqlalchemy.models import Base  # noqa: E402
from swen.infrastructure.persistence.sqlalchemy.repositories.factory import (  # noqa: E402
    create_ai_provider_from_settings,
)
from swen.presentation.api.config import get_api_settings  # noqa: E402
from swen.presentation.api.dependencies import get_engine  # noqa: E402
from swen.presentation.api.exception_handlers import (  # noqa: E402
    setup_exception_handlers,
)
from swen.presentation.api.routers import (  # noqa: E402
    accounts_router,
    admin_router,
    ai_router,
    analytics_router,
    auth_router,
    credentials_router,
    dashboard_router,
    exports_router,
    imports_router,
    mappings_router,
    onboarding_router,
    preferences_router,
    sync_router,
    transactions_router,
)

# IdentityBase is now same as Base
from swen_config.settings import Settings  # noqa: E402

logger = logging.getLogger(__name__)

# API version info
API_VERSION = "1.0.0"
API_V1_PREFIX = "/api/v1"

# OpenAPI tags metadata for documentation
OPENAPI_TAGS = [
    {
        "name": "Authentication",
        "description": """User authentication and session management.

**Registration & Login:**
- Register new accounts with email/password
- Login to obtain JWT tokens
- Refresh tokens before expiry

**Security:**
- Passwords are securely hashed (bcrypt)
- JWT tokens for stateless authentication
- Account lockout after failed attempts
""",
    },
    {
        "name": "Credentials",
        "description": """Bank credential management for FinTS connections.

**Features:**
- Securely store bank login credentials (encrypted at rest)
- Lookup bank information by BLZ (German bank code)
- Test connections before syncing

**Supported Banks:**
- All German banks with FinTS/HBCI interface
- Uses Deutsche Kreditwirtschaft institute directory

**TAN Methods:**
- `946`: SecureGo plus / Direktfreigabe (decoupled, recommended)
- `944`: SecureGo
- `962`: Smart-TAN plus manual
- `972`: chipTAN optical
- `982`: photoTAN
""",
    },
    {
        "name": "Accounts",
        "description": """Chart of accounts management (double-entry bookkeeping).

**Account Types:**
- `asset`: Bank accounts, cash, receivables (normal debit balance)
- `liability`: Credit cards, loans, payables (normal credit balance)
- `equity`: Owner's equity, retained earnings
- `income`: Salary, interest, dividends (credit increases)
- `expense`: Groceries, rent, utilities (debit increases)

**Bank Accounts:**
- Automatically created when syncing with banks
- Mapped by IBAN for transaction import
""",
    },
    {
        "name": "Transactions",
        "description": """Transaction management and double-entry journal.

**Transaction States:**
- `draft`: Imported but not finalized, can be edited
- `posted`: Finalized, affects account balances

**Features:**
- Automatic internal transfer detection between your accounts
- Double-entry bookkeeping (every transaction has balanced debits/credits)
- Filter by date range, account, or status
""",
    },
    {
        "name": "Dashboard",
        "description": """Financial summaries for quick overview.

**Available Data:**
- Income/expense totals for any period
- Current account balances
- Spending breakdown by category (expense accounts)
- Recent transactions

**Time Periods:**
- Specify `days` to look back from today
- Or specify `month` in YYYY-MM format
- Defaults to current month
""",
    },
    {
        "name": "Analytics",
        "description": """Financial analytics for charts and visualizations.

**Time Series Data (for line/bar charts):**
- `/spending/over-time` - Monthly spending by category
- `/income/over-time` - Monthly income totals
- `/net-income/over-time` - Monthly savings (income - expenses)

**Breakdown Data (for pie charts):**
- `/spending/breakdown` - Spending distribution by category

**Chart Types Supported:**
- Line charts (income trends, savings)
- Stacked bar charts (spending by category)
- Pie/donut charts (spending breakdown)
- Multi-line charts (category comparison)
""",
    },
    {
        "name": "Sync",
        "description": """Bank transaction synchronization via FinTS.

**How it works:**
1. Connects to your bank using stored credentials
2. Fetches transactions for the specified date range
3. Imports new transactions (skips duplicates)
4. Detects internal transfers between your accounts

**TAN Handling:**
- **Decoupled TAN** (SecureGo plus, pushTAN): API waits up to 5 minutes for approval
- **Interactive TAN** (photoTAN, chipTAN): Use CLI instead

**Important:** Set HTTP client timeout to 6+ minutes for TAN-requiring operations.
""",
    },
    {
        "name": "Exports",
        "description": """Data export for backup and analysis.

**Export Types:**
- `/exports/transactions` - Export transaction history
- `/exports/accounts` - Export chart of accounts
- `/exports/full` - Full backup (transactions + accounts + mappings)

**Filters:**
- Filter by days (history range)
- Filter by status (posted/draft)
- Filter by account type or IBAN

**Use Cases:**
- Spreadsheet analysis
- Data backup before migrations
- Reporting
""",
    },
    {
        "name": "Imports",
        "description": """Transaction import history and statistics.

**Import Statuses:**
- `success` - Transaction successfully imported
- `failed` - Import failed (see error_message)
- `pending` - Awaiting review
- `duplicate` - Already imported (skipped)
- `skipped` - Filtered out by rules

**Use Cases:**
- Troubleshoot sync issues
- Audit import history
- Monitor import health
""",
    },
    {
        "name": "Mappings",
        "description": """Bank account to ledger account mappings.

Maps bank accounts (identified by IBAN) to accounting accounts
in your chart of accounts.

**Created automatically** when you sync from a bank and a new
account is detected.

**Use Cases:**
- View which bank accounts are connected
- Check mapping configuration
""",
    },
    {
        "name": "Preferences",
        "description": """User preference management.

**Sync Settings:**
- `auto_post_transactions` - Auto-finalize imported transactions

**Display Settings:**
- `default_currency` - Default currency (EUR, USD, etc.)
- `show_draft_transactions` - Include drafts in lists
- `default_date_range_days` - Default filter range
""",
    },
    {
        "name": "Onboarding",
        "description": """New user onboarding and setup status.

**Onboarding Flow:**
1. Initialize expense accounts (templates)
2. Connect first bank
3. Add more banks (optional)
4. Add manual accounts (optional)

**Status is derived from existing data:**
- `accounts_initialized` - True if expense accounts exist
- `first_bank_connected` - True if bank credentials exist
- `has_transactions` - True if transactions exist
""",
    },
    {
        "name": "Health",
        "description": "Service health monitoring endpoints.",
    },
    {
        "name": "Info",
        "description": "API information and discovery.",
    },
]


async def _check_ai_health() -> None:
    """Check AI provider health at startup, auto-pulling model if needed."""
    settings = get_settings()
    if not settings.ai_enabled:
        logger.info("AI counter-account resolution is disabled")
        return

    logger.info(
        "Checking AI provider (Ollama at %s, model: %s)...",
        settings.ollama_base_url,
        settings.ai_ollama_model,
    )

    ai_provider = create_ai_provider_from_settings()
    if ai_provider is None:
        logger.warning("AI provider could not be created")
        return

    try:
        # Use ensure_model_available which will auto-pull if needed
        is_ready = await ai_provider.ensure_model_available(auto_pull=True)
        if is_ready:
            logger.info(
                "✓ AI provider ready (model '%s' available)",
                settings.ai_ollama_model,
            )
        else:
            logger.warning(
                "✗ AI provider not ready. AI-powered counter-account resolution "
                "will be unavailable until the model is downloaded.",
            )
    except Exception as e:
        logger.warning(
            "✗ AI health check failed: %s. Ensure Ollama is running at %s",
            e,
            settings.ollama_base_url,
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events, including database initialization.
    """
    # Startup
    logger.info("Starting SWEN API v%s...", API_VERSION)

    # Get the shared engine (this initializes the singleton)
    engine = get_engine()

    # Initialize database schema (idempotent - only creates tables if they don't exist)
    logger.info("Initializing database schema...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database schema initialized successfully")

    # Check AI provider health
    await _check_ai_health()

    yield

    # Shutdown - dispose the shared engine and its connection pool
    logger.info("Shutting down SWEN API...")
    await engine.dispose()
    logger.info("Database connections closed")


def create_v1_router() -> APIRouter:
    """Create the v1 API router with all endpoints.

    Returns
    -------
    APIRouter with all v1 endpoints mounted.
    """
    v1_router = APIRouter()

    # Mount all routers under v1
    v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    v1_router.include_router(admin_router, tags=["Admin"])
    v1_router.include_router(accounts_router, prefix="/accounts", tags=["Accounts"])
    v1_router.include_router(
        credentials_router,
        prefix="/credentials",
        tags=["Credentials"],
    )
    v1_router.include_router(
        transactions_router,
        prefix="/transactions",
        tags=["Transactions"],
    )
    v1_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
    v1_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
    v1_router.include_router(sync_router, prefix="/sync", tags=["Sync"])
    v1_router.include_router(exports_router, prefix="/exports", tags=["Exports"])
    v1_router.include_router(imports_router, prefix="/imports", tags=["Imports"])
    v1_router.include_router(mappings_router, prefix="/mappings", tags=["Mappings"])
    v1_router.include_router(
        onboarding_router,
        prefix="/onboarding",
        tags=["Onboarding"],
    )
    v1_router.include_router(
        preferences_router,
        prefix="/preferences",
        tags=["Preferences"],
    )
    v1_router.include_router(
        ai_router,
        prefix="/ai",
        tags=["AI"],
    )

    return v1_router


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Parameters
    ----------
    settings
        Optional settings override for testing.

    Returns
    -------
    Configured FastAPI application instance.
    """
    if settings is None:
        settings = get_api_settings()

    # Get app name from main settings
    app_name = get_settings().app_name

    app = FastAPI(
        title=f"{app_name} API",
        description=(
            "A **double-entry bookkeeping** system with "
            "**automated bank synchronization** via FinTS/HBCI."
        ),
        version=API_VERSION,
        docs_url="/docs" if settings.api_debug else None,
        redoc_url="/redoc" if settings.api_debug else None,
        openapi_url="/openapi.json" if settings.api_debug else None,
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register domain exception handlers for consistent error responses
    setup_exception_handlers(app)

    # Include versioned API router
    app.include_router(create_v1_router(), prefix=API_V1_PREFIX)

    # Health check endpoint (unversioned - always accessible)
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        """Health check endpoint.

        Returns service status and version info.
        Unversioned for load balancer/monitoring compatibility.
        """
        return {
            "status": "healthy",
            "version": API_VERSION,
            "api_versions": ["v1"],
        }

    # Root endpoint with API info
    @app.get("/", tags=["Info"])
    async def root() -> dict:
        """API root endpoint with version information."""
        return {
            "name": f"{app_name} API",
            "version": API_VERSION,
            "docs": "/docs" if settings.api_debug else None,
            "api_base": API_V1_PREFIX,
            "endpoints": {
                "health": "/health",
                "auth": f"{API_V1_PREFIX}/auth",
                "accounts": f"{API_V1_PREFIX}/accounts",
                "transactions": f"{API_V1_PREFIX}/transactions",
                "credentials": f"{API_V1_PREFIX}/credentials",
                "dashboard": f"{API_V1_PREFIX}/dashboard",
                "analytics": f"{API_V1_PREFIX}/analytics",
                "sync": f"{API_V1_PREFIX}/sync",
            },
        }

    return app


# Application instance for uvicorn
app = create_app()
