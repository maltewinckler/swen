"""FastAPI application with lifespan management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from swen_ml.config.settings import get_settings
from swen_ml.models.encoder import Encoder
from swen_ml.models.nli import NLIClassifier


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


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load models at startup, cleanup at shutdown."""
    settings = get_settings()

    logger.info("Loading embedding model: %s", settings.embedding_model)
    app.state.encoder = Encoder.load(settings.embedding_model)
    app.state.encoder.warmup()
    logger.info("Embedding model loaded (dim=%d)", app.state.encoder.dimension)

    logger.info("Loading NLI model: %s", settings.nli_model)
    app.state.nli = NLIClassifier.load(settings.nli_model)
    app.state.nli.warmup(["Test"])
    logger.info("NLI model loaded")

    logger.info("ML service ready")
    yield

    logger.info("Shutting down")
    del app.state.encoder
    del app.state.nli


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
