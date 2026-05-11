import logging

from fastapi import APIRouter, HTTPException, status

from swen.application.commands.banking import (
    SetupBankCommand,
)
from swen.application.dtos.banking import SetupBankRequestDTO
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.credentials import (
    SetupBankRequest,
    SetupBankResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/{blz}",
    summary="Setup bank connection and import accounts",
    responses={
        200: {"description": "Bank accounts imported successfully"},
        400: {"description": "Invalid BLZ format"},
        404: {"description": "Credentials not found"},
        503: {"description": "Connection failed"},
        504: {"description": "TAN approval timeout"},
    },
)
async def setup_bank_accounts(
    blz: str,
    factory: RepoFactory,
    request: SetupBankRequest,
) -> SetupBankResponse:
    """Import discovered bank accounts with user injected custom names."""
    # Validate BLZ format
    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )

    # SetupBankCommand handles credential loading, TAN settings, and import
    command = SetupBankCommand.from_factory(factory)
    try:
        setup_bank_request_dto = SetupBankRequestDTO(blz=blz, **request.model_dump())
        result = await command.execute(setup_bank_request_dto)
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    return SetupBankResponse(**result.model_dump())
