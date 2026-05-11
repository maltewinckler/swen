"""Credentials CRUD routers.

Has
* GET /credentials - list stored credentials (metadata only, no sensitive data)
* POST /credentials - store new credentials (with bank lookup and validation)
* DELETE /credentials/{blz} - delete credentials for a bank
"""

import logging

from fastapi import APIRouter, HTTPException, status

from swen.application.commands import StoreCredentialsCommand
from swen.application.queries import ListCredentialsQuery
from swen.application.queries.banking import LookupBankQuery
from swen.domain.banking.value_objects import BankCredentials
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.credentials import (
    CredentialCreateRequest,
    CredentialCreateResponse,
    CredentialListResponse,
    CredentialResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    summary="List stored credentials",
    responses={
        200: {"description": "List of stored credentials"},
    },
)
async def list_credentials(
    factory: RepoFactory,
) -> CredentialListResponse:
    """
    List all stored bank credentials for the current user.

    Returns metadata only (BLZ, label) - sensitive data (username, PIN)
    is never exposed.
    """
    query = ListCredentialsQuery.from_factory(factory)
    result = await query.execute()

    return CredentialListResponse(
        credentials=[
            CredentialResponse(
                credential_id=cred.credential_id,
                blz=cred.blz,
                label=cred.label,
            )
            for cred in result.credentials
        ],
        total=result.total_count,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Store bank credentials",
    responses={
        201: {"description": "Credentials stored successfully"},
        400: {"description": "Invalid input or bank not found"},
        409: {"description": "Credentials already exist for this bank"},
    },
)
async def store_credentials(
    request: CredentialCreateRequest,
    factory: RepoFactory,
) -> CredentialCreateResponse:
    """
    Store bank credentials securely for automated sync.

    The credentials are encrypted before storage. Bank name is automatically
    looked up from the bank information directory.

    Common TAN methods:
    - 946: SecureGo plus / Direktfreigabe (decoupled)
    - 944: SecureGo
    - 962: Smart-TAN plus manual
    - 972: chipTAN optical
    - 982: photoTAN
    """
    # Lookup bank info
    lookup = LookupBankQuery.from_factory(factory)
    bank_info = await lookup.execute(request.blz)

    if bank_info is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bank with BLZ {request.blz} not found in bank directory",
        )

    # Create credentials value object
    try:
        credentials = BankCredentials.from_plain(
            blz=request.blz,
            username=request.username,
            pin=request.pin,
        )
    except ValueError as e:
        logger.warning("Invalid credentials format for BLZ %s: %s", request.blz, e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials. Check your BLZ, username, and PIN.",
        ) from e

    # Store credentials using command
    command = StoreCredentialsCommand.from_factory(factory)

    try:
        credential_id = await command.execute(
            credentials=credentials,
            label=bank_info.name,
            tan_method=request.tan_method,
            tan_medium=request.tan_medium,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Credentials stored for BLZ %s", request.blz)

    return CredentialCreateResponse(
        credential_id=credential_id,
        blz=request.blz,
        label=bank_info.name,
        message="Credentials stored successfully",
    )


@router.delete(
    "/{blz}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete stored credentials",
    responses={
        204: {"description": "Credentials deleted"},
        404: {"description": "Credentials not found"},
    },
)
async def delete_credentials(
    blz: str,
    factory: RepoFactory,
) -> None:
    """
    Delete stored credentials for a bank.

    This permanently removes the encrypted credentials from the database.
    """
    # Validate BLZ format
    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )

    query = ListCredentialsQuery.from_factory(factory)
    deleted = await query.delete(blz)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credentials found for BLZ {blz}",
        )

    await factory.session.commit()
    logger.info("Credentials deleted for BLZ %s", blz)
