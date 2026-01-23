"""Example storage endpoint."""

from uuid import UUID

from fastapi import APIRouter, Request
from swen_ml_contracts import StoreExampleRequest, StoreExampleResponse

from swen_ml.config.settings import get_settings
from swen_ml.storage.example_store import ExampleStore, get_example_path

router = APIRouter()


@router.post("/users/{user_id}/examples", response_model=StoreExampleResponse)
async def store_example(
    user_id: UUID,
    request: StoreExampleRequest,
    http_request: Request,
) -> StoreExampleResponse:
    """Store a posted transaction as a training example."""
    settings = get_settings()
    encoder = http_request.app.state.encoder

    # Build text for embedding
    parts = []
    if request.counterparty_name:
        parts.append(request.counterparty_name)
    parts.append(request.purpose)
    text = " ".join(parts)

    # Encode
    embedding = encoder.encode_single(text)

    # Load or create store
    path = get_example_path(settings.data_dir, user_id)
    store = ExampleStore.load_or_empty(path)

    # Add example
    store.add(
        embedding=embedding,
        account_id=str(request.account_id),
        account_number=request.account_number,
        text=text,
    )

    # Save
    store.save(path)

    return StoreExampleResponse(
        stored=True,
        total_examples=len(store),
        message=f"Stored example for account {request.account_number}",
    )
