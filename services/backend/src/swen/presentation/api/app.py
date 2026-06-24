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
from functools import lru_cache
from typing import AsyncGenerator

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine

from swen.infrastructure.persistence.sqlalchemy.models import Base
from swen.presentation.api.accounting.routers import (
    accounts_router as accounting_accounts_router,
)
from swen.presentation.api.accounting.routers import (
    init_router as accounting_init_router,
)
from swen.presentation.api.accounting.routers.transactions import (
    router as transactions_router,
)
from swen.presentation.api.admin.routers.admin import router as admin_router
from swen.presentation.api.analytics.routers.analytics import router as analytics_router
from swen.presentation.api.analytics.routers.dashboard import router as dashboard_router
from swen.presentation.api.analytics.routers.exports import router as exports_router
from swen.presentation.api.auth.routers.auth import router as auth_router
from swen.presentation.api.banking.routers import (
    bank_accounts_router,
    bank_connections_router,
)
from swen.presentation.api.dependencies import get_engine, get_ml_client
from swen.presentation.api.exception_handlers import (
    setup_exception_handlers,
)
from swen.presentation.api.integration.routers import router as integration_router
from swen.presentation.api.integration.routers.imports import router as imports_router
from swen.presentation.api.integration.routers.mappings import router as mappings_router
from swen.presentation.api.integration.routers.sync import router as sync_router
from swen.presentation.api.onboarding.routers.onboarding import (
    router as onboarding_router,
)
from swen.presentation.api.open_api import OPENAPI_TAGS
from swen.presentation.api.settings.routers.preferences import (
    router as preferences_router,
)
from swen_config.settings import Settings, get_settings


@lru_cache(maxsize=1)
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


logger = logging.getLogger(__name__)

# API version info
API_VERSION = "1.0.0"
API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting SWEN API v%s...", API_VERSION)
    engine = get_engine()
    await _init_database_schema(engine)
    await _check_ml_service_health()
    yield

    # Shutdown - dispose the shared engine and its connection pool
    logger.info("Shutting down SWEN API...")
    await engine.dispose()
    logger.info("Database connections closed")


async def _init_database_schema(engine: AsyncEngine) -> None:
    """Initialize database schema (if not existent) and verify connectivity."""
    logger.info("Initializing database schema...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except ConnectionRefusedError:
        logger.critical("Could not connect to the database.")
        raise SystemExit(1) from None

    logger.info("Database schema initialized successfully")


async def _check_ml_service_health() -> None:
    """Check ML service availability on startup."""
    ml_client = get_ml_client()

    if not ml_client.enabled:
        logger.info("ML service disabled (SWEN_ML_SERVICE_ENABLED=false)")
        return

    try:
        health = await ml_client.health_check()
        if health and health.status == "ok":
            models_info = []
            if health.embedding_model_loaded:
                models_info.append(f"embeddings: {health.embedding_model_name}")
            logger.info(
                "ML service healthy: %s (models: %s)",
                health.status,
                ", ".join(models_info) if models_info else "none",
            )
        else:
            logger.warning(
                "ML service unhealthy or returned unexpected response: %s",
                health,
            )
    except Exception as e:
        logger.warning(
            "ML service unavailable at startup (classification will fail): %s",
            str(e),
        )


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
    v1_router.include_router(
        accounting_accounts_router, prefix="/accounts", tags=["Accounts"]
    )
    v1_router.include_router(
        accounting_init_router, prefix="/accounts", tags=["Accounts"]
    )
    v1_router.include_router(
        bank_connections_router,
        prefix="/bank-connections",
        tags=["Banking"],
    )
    v1_router.include_router(
        bank_accounts_router,
        prefix="/bank-accounts",
        tags=["Banking"],
    )
    v1_router.include_router(
        integration_router,
        prefix="/integration",
        tags=["Integration"],
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
    # Configure logging on first app creation (not on module import)
    _configure_logging()

    if settings is None:
        settings = get_settings()

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
