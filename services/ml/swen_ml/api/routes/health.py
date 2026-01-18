"""Health check endpoint."""

from fastapi import APIRouter, Request
from swen_ml_contracts import HealthResponse

from swen_ml import __version__
from swen_ml.api.dependencies import SettingsDep

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request, settings: SettingsDep) -> HealthResponse:
    classifier = request.app.state.classifier
    return HealthResponse(
        status="ok",
        version=__version__,
        model_loaded=True,
        model_name=settings.sentence_transformer_model,
        total_users=len(classifier.store.list_users()),
    )
