from fastapi import APIRouter, Request
from swen_ml_contracts import HealthResponse

from swen_ml.config.settings import get_settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Check service health and model status."""
    settings = get_settings()

    encoder_loaded = hasattr(request.app.state, "encoder")

    return HealthResponse(
        status="ok" if encoder_loaded else "degraded",
        version="0.1.0",
        embedding_model_loaded=encoder_loaded,
        embedding_model_name=settings.encoder_model,
        users_cached=0,  # TODO: Get from cache
    )
