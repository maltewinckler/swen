"""Account anchor embedding endpoint."""

from fastapi import APIRouter, Request
from swen_ml_contracts import EmbedAccountsRequest, EmbedAccountsResponse

from swen_ml.config.settings import get_settings
from swen_ml.storage.anchor_store import AnchorStore, get_anchor_path

router = APIRouter()


@router.post("/users/{user_id}/accounts/embed", response_model=EmbedAccountsResponse)
async def embed_accounts(
    request: EmbedAccountsRequest,
    http_request: Request,
) -> EmbedAccountsResponse:
    """Compute and store anchor embeddings for accounts."""
    settings = get_settings()
    encoder = http_request.app.state.encoder

    if not request.accounts:
        return EmbedAccountsResponse(embedded=0, message="No accounts provided")

    # Build texts from account name + description
    texts = []
    for account in request.accounts:
        text = account.name
        if account.description:
            text = f"{account.name}: {account.description}"
        texts.append(text)

    # Encode all accounts
    embeddings = encoder.encode(texts)

    # Create anchor store
    store = AnchorStore()
    store.set(
        embeddings=embeddings,
        account_ids=[str(a.account_id) for a in request.accounts],
        account_numbers=[a.account_number for a in request.accounts],
        account_names=[a.name for a in request.accounts],
    )

    # Save
    path = get_anchor_path(settings.data_dir, request.user_id)
    store.save(path)

    return EmbedAccountsResponse(
        embedded=len(request.accounts),
        message=f"Embedded {len(request.accounts)} account anchors",
    )
