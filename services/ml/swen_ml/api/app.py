"""FastAPI application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from swen_ml import __version__
from swen_ml.config.settings import Settings
from swen_ml.inference.encoder import TransactionEncoder
from swen_ml.inference.similarity_classifier import SimilarityClassifier
from swen_ml.storage.embedding_store import EmbeddingStore

from .routes import accounts, classify, examples, health, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting SWEN ML Service v%s", __version__)

    settings = Settings()
    logger.info("Loading model: %s", settings.sentence_transformer_model)

    encoder = TransactionEncoder(
        model_name=settings.sentence_transformer_model,
        cache_folder=settings.hf_cache_path,
    )
    store = EmbeddingStore(settings.embedding_storage_path)
    classifier = SimilarityClassifier(
        encoder=encoder,
        store=store,
        similarity_threshold=settings.similarity_threshold,
        description_threshold=settings.description_threshold,
        max_examples_per_account=settings.max_examples_per_account,
    )

    app.state.settings = settings
    app.state.classifier = classifier

    logger.info("ML Service ready")
    yield
    logger.info("Shutting down ML Service")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SWEN ML Service",
        description="Transaction classification using sentence embeddings",
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(classify.router)
    app.include_router(examples.router)
    app.include_router(accounts.router)
    app.include_router(users.router)
    return app


app = create_app()
