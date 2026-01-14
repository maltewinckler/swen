"""AI router for model management, settings, and testing.

Provides endpoints for:
- Getting AI service status
- Listing available models
- Downloading new models with streaming progress
- Managing user AI settings
- Testing AI classification
"""

import json
import logging
import time
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from swen.domain.accounting.repositories import AccountRepository
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.value_objects import CounterAccountOption
from swen.infrastructure.integration.ai import (
    OllamaCounterAccountProvider,
    OllamaModelRegistry,
)
from swen.presentation.api.dependencies import RepoFactory
from swen_config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


class AIStatusResponse(BaseModel):
    """Current AI service status."""

    enabled: bool = Field(description="Whether AI classification is enabled in config")
    provider: str = Field(description="AI provider name (e.g., 'ollama')")
    current_model: str = Field(description="Currently configured model name")
    model_available: bool = Field(description="Whether the current model is installed")
    service_healthy: bool = Field(description="Whether the AI service is reachable")


class AIModelResponse(BaseModel):
    """Information about an AI model."""

    name: str = Field(description="Model identifier (e.g., 'qwen2.5:3b')")
    display_name: str = Field(description="Human-readable name")
    description: str = Field(description="Brief model description")
    size_display: str = Field(description="Human-readable size (e.g., '1.9 GB')")
    status: str = Field(description="Status: available, downloading, not_installed")
    is_recommended: bool = Field(
        description="Whether this is a curated recommended model",
    )
    download_progress: Optional[float] = Field(
        None,
        description="Download progress 0.0-1.0 if downloading",
    )


class AIModelsListResponse(BaseModel):
    """List of available AI models."""

    provider: str = Field(description="AI provider name")
    models: list[AIModelResponse] = Field(description="Available models")


class ModelPullStartResponse(BaseModel):
    """Response when starting a model download."""

    model_name: str = Field(description="Model being downloaded")
    message: str = Field(description="Status message")


class AISettingsResponse(BaseModel):
    """User's AI classification settings."""

    enabled: bool = Field(
        description="Whether AI classification is enabled for this user",
    )
    model_name: str = Field(description="Preferred AI model for classification")
    min_confidence: float = Field(description="Minimum confidence threshold (0.0-1.0)")


class AISettingsUpdateRequest(BaseModel):
    """Request to update AI settings."""

    enabled: Optional[bool] = Field(
        None,
        description="Enable/disable AI classification",
    )
    model_name: Optional[str] = Field(None, description="Change preferred model")
    min_confidence: Optional[float] = Field(
        None,
        description="Change confidence threshold (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )


class AITestRequest(BaseModel):
    """Request to test AI classification with sample transaction data."""

    counterparty_name: str = Field(
        description="Name of the counterparty (e.g., 'REWE SAGT DANKE')",
    )
    purpose: str = Field(
        description="Transaction purpose/description (e.g., 'KARTENZAHLUNG EC')",
    )
    amount: float = Field(description="Transaction amount (negative for expenses)")
    model_name: Optional[str] = Field(
        None,
        description="Model to use (defaults to user preference or config)",
    )


class AITestExample(BaseModel):
    """A sample transaction for testing AI classification."""

    id: str = Field(description="Unique example identifier")
    label: str = Field(description="Short label for the example")
    counterparty_name: str = Field(description="Counterparty name")
    purpose: str = Field(description="Transaction purpose")
    amount: float = Field(description="Transaction amount")
    category_hint: str = Field(description="Expected category (for reference)")


class AITestAccountSuggestion(BaseModel):
    """An AI-suggested account."""

    account_id: str = Field(description="Account UUID")
    account_number: str = Field(description="Account number")
    account_name: str = Field(description="Account display name")
    confidence: float = Field(description="Confidence score 0.0-1.0")
    reasoning: Optional[str] = Field(None, description="AI's reasoning")


class AITestResponse(BaseModel):
    """Result of AI classification test."""

    model_used: str = Field(description="Model that performed the classification")
    suggestion: Optional[AITestAccountSuggestion] = Field(
        None,
        description="AI's suggestion (None if AI couldn't classify)",
    )
    meets_confidence_threshold: bool = Field(
        description="Whether confidence meets the configured threshold",
    )
    processing_time_ms: float = Field(description="Time taken in milliseconds")


def _get_registry() -> OllamaModelRegistry:
    """Get the Ollama model registry with settings from config."""
    settings = get_settings()
    return OllamaModelRegistry(base_url=settings.ollama_base_url)


@router.get(
    "/status",
    summary="Get AI service status",
    responses={
        200: {"description": "Current AI status"},
    },
)
async def get_ai_status() -> AIStatusResponse:
    """
    Get the current status of the AI classification service.

    Returns information about:
    - Whether AI is enabled in the configuration
    - The configured model
    - Whether the model is installed and ready
    - Whether the AI service is reachable
    """
    settings = get_settings()
    registry = _get_registry()

    service_healthy = await registry.is_healthy()
    model_available = False

    if service_healthy:
        model_available = await registry.is_model_available(settings.ai_ollama_model)

    return AIStatusResponse(
        enabled=settings.ai_enabled,
        provider=settings.ai_provider,
        current_model=settings.ai_ollama_model,
        model_available=model_available,
        service_healthy=service_healthy,
    )


@router.get(
    "/models",
    summary="List available AI models",
    responses={
        200: {"description": "List of available models"},
        503: {"description": "AI service unavailable"},
    },
)
async def list_models() -> AIModelsListResponse:
    """
    List all available AI models.

    Returns both installed models and recommended models that can be downloaded.
    Models are sorted with installed models first, then by name.
    """
    registry = _get_registry()

    if not await registry.is_healthy():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service (Ollama) is not reachable. Please ensure it is running.",
        )

    models = await registry.list_models()

    return AIModelsListResponse(
        provider=registry.provider_name,
        models=[
            AIModelResponse(
                name=m.name,
                display_name=m.display_name,
                description=m.description,
                size_display=m.size_display,
                status=m.status.value,
                is_recommended=m.is_recommended,
                download_progress=m.download_progress,
            )
            for m in models
        ],
    )


@router.post(
    "/models/{model_name}/pull",
    summary="Start downloading a model",
    responses={
        200: {"description": "Download started, stream progress via SSE"},
        400: {"description": "Model already installed or invalid name"},
        503: {"description": "AI service unavailable"},
    },
)
async def pull_model(model_name: str) -> StreamingResponse:
    """
    Download an AI model with streaming progress.

    Returns a Server-Sent Events (SSE) stream with download progress updates.
    Connect with EventSource in the browser to receive real-time updates.

    **Example JavaScript:**
    ```javascript
    const eventSource = new EventSource('/api/v1/ai/models/qwen2.5:3b/pull');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(`Progress: ${data.progress * 100}%`);
        if (data.is_complete) eventSource.close();
    };
    ```
    """
    registry = _get_registry()

    if not await registry.is_healthy():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service (Ollama) is not reachable",
        )

    # Check if already installed
    if await registry.is_model_available(model_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model_name}' is already installed",
        )

    # Check if it's a known model
    model_info = await registry.get_model_info(model_name)
    if model_info is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model: '{model_name}'. Use one of the recommended models.",
        )

    logger.info("Starting model download: %s", model_name)

    async def event_stream():
        """Generate SSE events for download progress."""
        try:
            async for progress in registry.pull_model(model_name):
                # Format as SSE event
                data = {
                    "model_name": progress.model_name,
                    "status": progress.status,
                    "progress": progress.progress,
                    "completed_bytes": progress.completed_bytes,
                    "total_bytes": progress.total_bytes,
                    "is_complete": progress.is_complete,
                    "error": progress.error,
                }
                yield f"data: {json.dumps(data)}\n\n"

                if progress.is_complete or progress.error:
                    break

        except Exception as e:
            error_data = {
                "model_name": model_name,
                "status": "error",
                "error": str(e),
                "is_complete": False,
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get(
    "/models/{model_name}",
    summary="Get model info",
    responses={
        200: {"description": "Model information"},
        404: {"description": "Model not found"},
    },
)
async def get_model_info(model_name: str) -> AIModelResponse:
    """
    Get information about a specific AI model.

    Returns model details including installation status.
    """
    registry = _get_registry()

    model = await registry.get_model_info(model_name)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_name}' not found",
        )

    return AIModelResponse(
        name=model.name,
        display_name=model.display_name,
        description=model.description,
        size_display=model.size_display,
        status=model.status.value,
        is_recommended=model.is_recommended,
        download_progress=model.download_progress,
    )


@router.get(
    "/settings",
    summary="Get user AI settings",
    responses={
        200: {"description": "User's AI settings"},
    },
)
async def get_ai_settings(factory: RepoFactory) -> AISettingsResponse:
    """
    Get the current user's AI classification settings.

    These settings control how AI-powered counter-account resolution
    behaves for this user's transactions.
    """
    settings_repo = factory.user_settings_repository()
    settings = await settings_repo.get_or_create()

    return AISettingsResponse(
        enabled=settings.ai.enabled,
        model_name=settings.ai.model_name,
        min_confidence=settings.ai.min_confidence,
    )


@router.patch(
    "/settings",
    summary="Update user AI settings",
    responses={
        200: {"description": "Updated AI settings"},
        400: {"description": "Invalid settings or model not available"},
    },
)
async def update_ai_settings(
    request: AISettingsUpdateRequest,
    factory: RepoFactory,
) -> AISettingsResponse:
    """
    Update the current user's AI classification settings.

    Only provided fields will be updated; others remain unchanged.

    **Note:** If changing the model, ensure it is installed first
    using the `/ai/models/{name}/pull` endpoint.
    """
    # Check if any update is provided
    if all(
        v is None for v in [request.enabled, request.model_name, request.min_confidence]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one setting must be provided",
        )

    # If model is being changed, verify it's available
    if request.model_name is not None:
        registry = _get_registry()
        if not await registry.is_model_available(request.model_name):
            model_info = await registry.get_model_info(request.model_name)
            if model_info is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown model: '{request.model_name}'",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{request.model_name}' is not installed. "
                f"Download it first using POST /ai/models/{request.model_name}/pull",
            )

    settings_repo = factory.user_settings_repository()
    settings = await settings_repo.get_or_create()

    # Update AI settings
    settings.update_ai(
        enabled=request.enabled,
        model_name=request.model_name,
        min_confidence=request.min_confidence,
    )

    await settings_repo.save(settings)
    await factory.session.commit()

    logger.info("User %s updated AI settings", factory.current_user.user_id)

    return AISettingsResponse(
        enabled=settings.ai.enabled,
        model_name=settings.ai.model_name,
        min_confidence=settings.ai.min_confidence,
    )


@router.post(
    "/test",
    summary="Test AI classification",
    responses={
        200: {"description": "AI classification result"},
        400: {"description": "AI not enabled or model not available"},
        503: {"description": "AI service unavailable"},
    },
)
async def test_ai_classification(
    request: AITestRequest,
    factory: RepoFactory,
) -> AITestResponse:
    """
    Test AI classification with sample transaction data.

    This endpoint allows you to test how the AI classifies transactions
    without actually creating any transactions. Useful for:
    - Evaluating model performance before switching
    - Understanding how different transactions are classified
    - Debugging classification issues

    **Example:**
    ```json
    {
        "counterparty_name": "REWE SAGT DANKE",
        "purpose": "KARTENZAHLUNG EC 4500",
        "amount": -45.67
    }
    ```
    """
    start_time = time.perf_counter()

    # Get user's AI settings
    settings_repo = factory.user_settings_repository()
    settings = await settings_repo.get_or_create()

    # Check if AI is enabled
    if not settings.ai.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="AI classification is disabled in your settings. "
            "Enable it via PATCH /ai/settings",
        )

    # Determine which model to use
    model_to_use = request.model_name or settings.ai.model_name
    app_settings = get_settings()

    # Check if model is available
    registry = _get_registry()
    if not await registry.is_healthy():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service (Ollama) is not reachable",
        )

    if not await registry.is_model_available(model_to_use):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model_to_use}' is not installed. "
            f"Download it first using POST /ai/models/{model_to_use}/pull",
        )

    # Create AI provider with the selected model
    ai_provider = OllamaCounterAccountProvider(
        model=model_to_use,
        base_url=app_settings.ollama_base_url,
        min_confidence=settings.ai.min_confidence,
        timeout=app_settings.ai_ollama_timeout,
    )

    # Create a synthetic bank transaction
    today = date.today()
    test_transaction = BankTransaction(
        booking_date=today,
        value_date=today,
        amount=Decimal(str(request.amount)),
        currency="EUR",
        applicant_name=request.counterparty_name or None,
        purpose=request.purpose or "Test transaction",
    )

    # Get available accounts for AI context
    account_repo: AccountRepository = factory.account_repository()
    expense_accounts = await account_repo.find_by_type("expense")
    income_accounts = await account_repo.find_by_type("income")

    available_accounts = [
        CounterAccountOption(
            account_id=acc.id,
            account_number=acc.account_number,
            name=acc.name,
            account_type=acc.account_type.value,  # AccountType enum to string
            description=acc.description,
        )
        for acc in expense_accounts + income_accounts
    ]

    if not available_accounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No expense or income accounts found. Create accounts first.",
        )

    # Call AI provider
    try:
        result = await ai_provider.resolve(test_transaction, available_accounts)
    except Exception as e:
        logger.error("AI classification failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI classification failed: {e!s}",
        ) from e

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    if result is None:
        return AITestResponse(
            model_used=model_to_use,
            suggestion=None,
            meets_confidence_threshold=False,
            processing_time_ms=round(elapsed_ms, 2),
        )

    # Find the account details
    matched_account = None
    for acc in expense_accounts + income_accounts:
        if acc.id == result.counter_account_id:
            matched_account = acc
            break

    suggestion = None
    if matched_account:
        suggestion = AITestAccountSuggestion(
            account_id=str(result.counter_account_id),
            account_number=matched_account.account_number,
            account_name=matched_account.name,
            confidence=result.confidence,
            reasoning=result.reasoning,
        )

    return AITestResponse(
        model_used=model_to_use,
        suggestion=suggestion,
        meets_confidence_threshold=result.is_confident(settings.ai.min_confidence),
        processing_time_ms=round(elapsed_ms, 2),
    )


# Example transactions from real German banking data
# These represent actual transaction patterns for testing AI classification
TEST_EXAMPLES: list[AITestExample] = [
    AITestExample(
        id="grocery-rewe",
        label="Groceries (REWE)",
        counterparty_name="REWE.Berlin.Friedrichsh/Berlin",
        purpose="VISA Debitkartenumsatz vom 10.12.2025",
        amount=-5.18,
        category_hint="Lebensmittel / Groceries",
    ),
    AITestExample(
        id="grocery-lidl",
        label="Groceries (Lidl)",
        counterparty_name="Lidl.sagt.Danke/Berlin",
        purpose="VISA Debitkartenumsatz vom 20.11.2025",
        amount=-48.24,
        category_hint="Lebensmittel / Groceries",
    ),
    AITestExample(
        id="bakery",
        label="Bakery",
        counterparty_name="B.ckerei...Konditorei/Berlin",
        purpose="VISA Debitkartenumsatz vom 30.11.2025",
        amount=-10.50,
        category_hint="Lebensmittel / Groceries",
    ),
    AITestExample(
        id="salary",
        label="Salary",
        counterparty_name="Cashcow GmbH",
        purpose="Lohn/Gehalt/Rente Verdienstabrechnung 12.25/1",
        amount=2503.70,
        category_hint="Gehalt / Salary",
    ),
    AITestExample(
        id="utilities-gas",
        label="Gas Bill",
        counterparty_name="Stadtwerke Berlin",
        purpose="Lastschrift KD 10617910 Abschlag fuer Gas",
        amount=-100.00,
        category_hint="Nebenkosten / Utilities",
    ),
    AITestExample(
        id="utilities-electricity",
        label="Electricity Bill",
        counterparty_name="NaturStromHandel GmbH",
        purpose="Lastschrift Vertragsnummer 2554116-1 / Dezember 2025 / Abschlag Strom",
        amount=-32.00,
        category_hint="Nebenkosten / Utilities",
    ),
    AITestExample(
        id="telecom-mobile",
        label="Mobile Phone (Aldi Talk)",
        counterparty_name="E-Plus Service GmbH",
        purpose="Lastschrift Gebuehr fuer Kombi-Paket S (5G) Aldi Talk sagt DANKE",
        amount=-8.99,
        category_hint="Telekommunikation / Telecom",
    ),
    AITestExample(
        id="gym",
        label="Gym Membership",
        counterparty_name="FitX Deutschland GmbH",
        purpose="Lastschrift FitX Standard 24.00 EUR 01.12.25-31.12.25",
        amount=-24.00,
        category_hint="Sport / Fitness",
    ),
    AITestExample(
        id="sports-club",
        label="Sports Club Membership",
        counterparty_name="Budoka Kickboxen 1922 e.V.",
        purpose="Lastschrift Mitgliedschaftsbeitrag",
        amount=-105.00,
        category_hint="Sport / Verein",
    ),
    AITestExample(
        id="medical",
        label="Medical/Doctor",
        counterparty_name="Zahnarztpraxis Dr. med. Schmidt",
        purpose="Rechnung Zahnbehandlung vom 15.11.2025",
        amount=-185.50,
        category_hint="Gesundheit / Medical",
    ),
    AITestExample(
        id="transport-bike",
        label="Bike Sharing",
        counterparty_name="nextbike.GmbH.MR/Berlin",
        purpose="VISA Debitkartenumsatz vom 27.08.2025",
        amount=-1.50,
        category_hint="Transport / Mobility",
    ),
    AITestExample(
        id="gaming",
        label="Gaming (Steam)",
        counterparty_name="PAYPAL..STEAM.GAMES/2066609771",
        purpose="VISA Debitkartenumsatz vom 22.11.2025",
        amount=-9.99,
        category_hint="Unterhaltung / Entertainment",
    ),
    AITestExample(
        id="rent-income",
        label="Rent Income",
        counterparty_name="Max Mustermann",
        purpose="Dauerauftrag Miete",
        amount=250.00,
        category_hint="Mieteinnahmen / Rent Income",
    ),
    AITestExample(
        id="government",
        label="Government Fee",
        counterparty_name="Landeshauptkasse Berlin",
        purpose="SEPA Überweisung 1230944874747",
        amount=-20.00,
        category_hint="Gebühren / Fees",
    ),
]


@router.get(
    "/test/examples",
    summary="Get example transactions for testing",
    responses={
        200: {"description": "List of example transactions"},
    },
)
async def get_test_examples() -> list[AITestExample]:
    """
    Get a list of example transactions for testing AI classification.

    These are common German transaction patterns that can be used to
    quickly test how the AI classifies different transaction types.
    """
    return TEST_EXAMPLES
