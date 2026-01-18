"""FastAPI dependencies."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from swen_ml.config.settings import Settings
from swen_ml.inference.similarity_classifier import SimilarityClassifier


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_classifier(request: Request) -> SimilarityClassifier:
    return request.app.state.classifier


SettingsDep = Annotated[Settings, Depends(get_settings)]
ClassifierDep = Annotated[SimilarityClassifier, Depends(get_classifier)]
