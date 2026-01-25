"""FastAPI application with lifespan management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from swen_ml.config.settings import get_settings
from swen_ml.inference import ClassificationOrchestrator, SharedInfrastructure
from swen_ml.inference._models import create_encoder
from swen_ml.inference.classification.enrichment import (
    EnrichmentService,
    SearXNGAdapter,
)
from swen_ml.storage import Base, get_engine


def configure_logging() -> None:
    """Configure logging for the ML service."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set level for our package specifically
    logging.getLogger("swen_ml").setLevel(log_level)

    # Quiet noisy third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)


configure_logging()
logger = logging.getLogger(__name__)


async def _init_database(engine: AsyncEngine) -> None:
    """Initialize database tables."""
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")


def _log_settings() -> None:
    """Log current settings for debugging."""
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("SWEN ML Service Configuration")
    logger.info("=" * 60)
    logger.info("  Log level: %s", settings.log_level)
    logger.info("  Database: %s", settings.database_url.split("@")[-1])  # Hide password
    logger.info("  Data dir: %s (legacy)", settings.data_dir)
    logger.info("  Encoder:")
    logger.info("    Backend: %s", settings.encoder_backend)
    logger.info("    Model: %s", settings.encoder_model)
    if settings.encoder_backend == "huggingface":
        logger.info("    Pooling: %s", settings.encoder_pooling)
        logger.info("    Normalize: %s", settings.encoder_normalize)
        logger.info("    Max length: %d", settings.encoder_max_length)
    logger.info("  Thresholds:")
    logger.info("    Example high conf: %.2f", settings.example_high_confidence)
    logger.info("    Example accept: %.2f", settings.example_accept_threshold)
    logger.info("    Anchor accept: %.2f", settings.anchor_accept_threshold)
    logger.info("  Enrichment:")
    logger.info("    Enabled: %s", settings.enrichment_enabled)
    if settings.enrichment_enabled:
        logger.info("    SearXNG URL: %s", settings.enrichment_searxng_url)
        logger.info("    Cache TTL: %d days", settings.enrichment_cache_ttl_days)
        logger.info("    Rate limit: %.1fs", settings.enrichment_rate_limit_seconds)
    logger.info("=" * 60)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load models at startup, cleanup at shutdown."""
    settings = get_settings()

    # Log configuration
    _log_settings()

    # Initialize database
    engine = get_engine()
    await _init_database(engine)
    app.state.db_engine = engine

    # Load encoder using factory (supports multiple backends)
    logger.info(
        "Loading encoder: backend=%s, model=%s",
        settings.encoder_backend,
        settings.encoder_model,
    )
    encoder = create_encoder(settings)
    encoder.warmup()
    logger.info(
        "Encoder loaded: %s (dim=%d)",
        encoder.model_name,
        encoder.dimension,
    )

    # Initialize enrichment service (if enabled)
    enrichment_service: EnrichmentService | None = None
    if settings.enrichment_enabled:
        logger.info(
            "Initializing enrichment service: %s",
            settings.enrichment_searxng_url,
        )
        searxng_adapter = SearXNGAdapter(
            base_url=settings.enrichment_searxng_url,
            timeout=settings.enrichment_search_timeout,
        )
        enrichment_service = EnrichmentService(adapter=searxng_adapter)
        logger.info("Enrichment service ready")
    else:
        logger.info("Enrichment service disabled")

    # Create shared infrastructure
    infra = SharedInfrastructure.create(
        encoder=encoder,
        settings=settings,
        enrichment_service=enrichment_service,
    )

    # Create orchestrator and store in app state
    app.state.classification = ClassificationOrchestrator(infra)

    # Keep references for cleanup
    app.state.encoder = encoder
    app.state.enrichment_service = enrichment_service
    app.state.infra = infra

    logger.info("ML service ready - orchestrators initialized")
    yield

    logger.info("Shutting down")
    del app.state.classification
    del app.state.infra
    del app.state.encoder
    if app.state.enrichment_service:
        del app.state.enrichment_service

    # Close database connections
    await app.state.db_engine.dispose()
    del app.state.db_engine


def create_app() -> FastAPI:
    """Create FastAPI application."""
    from swen_ml.api.routes import accounts, classify, examples, health

    app = FastAPI(
        title="SWEN ML Service",
        description="Transaction classification service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(classify.router, tags=["classification"])
    app.include_router(examples.router, tags=["examples"])
    app.include_router(accounts.router, tags=["accounts"])

    return app


# For uvicorn
app = create_app()
