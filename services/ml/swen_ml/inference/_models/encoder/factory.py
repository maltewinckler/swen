"""Encoder factory for creating encoder instances based on configuration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

from .huggingface import HuggingFaceEncoder
from .protocol import Encoder
from .sentence_transformer import SentenceTransformerEncoder

if TYPE_CHECKING:
    from swen_ml.config.settings import Settings

logger = logging.getLogger(__name__)

EncoderBackend = Literal["sentence-transformers", "huggingface"]


def create_encoder(settings: Settings) -> Encoder:
    """Create an encoder based on settings.

    Parameters
    ----------
    settings
        Application settings containing encoder configuration.

    Returns
    -------
    Encoder
        Configured encoder instance.

    Raises
    ------
    ValueError
        If the encoder backend is not supported.
    """
    backend = settings.encoder_backend
    model = settings.encoder_model

    logger.info("Creating encoder: backend=%s, model=%s", backend, model)

    if backend == "sentence-transformers":
        return SentenceTransformerEncoder.load(model)

    if backend == "huggingface":
        return HuggingFaceEncoder.load(
            model_name=model,
            pooling=settings.encoder_pooling,
            normalize=settings.encoder_normalize,
            max_length=settings.encoder_max_length,
        )

    msg = f"Unknown encoder backend: {backend}"
    raise ValueError(msg)
