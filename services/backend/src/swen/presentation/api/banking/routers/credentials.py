"""Credentials CRUD routers.

Has
* GET /credentials - list stored credentials (metadata only, no sensitive data)
* POST /credentials - store new credentials (with bank lookup and validation)
* DELETE /credentials/{blz} - delete credentials for a bank
"""

import logging

from fastapi import APIRouter, HTTPException, status

from swen.application.banking.commands import (
    DeleteCredentialsCommand,
    StoreCredentialsCommand,
    UpdateCredentialsCommand,
)
from swen.application.banking.dtos import CredentialToStoreDTO, UpdateCredentialsDTO
from swen.application.banking.queries import ListCredentialsQuery
from swen.domain.banking.exceptions import CredentialsNotFoundError
from swen.domain.shared.value_objects import SecureString
from swen.presentation.api.banking.schemas.credentials import (
    CredentialToStore,
    CredentialToUpdate,
    StoredCredentialList,
)
from swen.presentation.api.dependencies import RepoFactory

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    summary="List stored credentials",
    responses={
        200: {"description": "List of stored credentials"},
    },
)
async def list_credentials(factory: RepoFactory) -> StoredCredentialList:
    """
    List all stored bank credentials for the current user.

    Returns metadata only (BLZ, label) - sensitive data (username, PIN)
    is never exposed.
    """
    query = ListCredentialsQuery.from_factory(factory)
    result = await query.execute()

    return StoredCredentialList.model_validate(result)


@router.post(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Store bank credentials",
    responses={
        204: {"description": "Credentials stored successfully"},
        400: {"description": "Invalid input"},
        409: {"description": "Credentials already exist for this bank"},
    },
)
async def store_credentials(
    request: CredentialToStore,
    factory: RepoFactory,
) -> None:
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
    credentials_to_store = CredentialToStoreDTO(
        blz=request.blz,
        username=SecureString(request.username),
        pin=SecureString(request.pin),
        tan_method=request.tan_method,
        tan_medium=request.tan_medium,
    )

    command = StoreCredentialsCommand.from_factory(factory)
    await command.execute(credential_to_store=credentials_to_store)
    logger.info("Credentials stored for BLZ %s", request.blz)


@router.patch(
    "/{blz}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update TAN settings for stored credentials",
    responses={
        204: {"description": "TAN settings updated"},
        400: {"description": "Invalid BLZ format"},
        404: {"description": "Credentials not found"},
    },
)
async def update_credentials_tan(
    blz: str,
    request: CredentialToUpdate,
    factory: RepoFactory,
) -> None:
    """
    Update the TAN method and medium for already-stored bank credentials.

    Call this after the user has selected a TAN method from the list
    returned by the /tan-methods endpoint.
    """
    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )
    username = request.username
    pin = request.pin
    dto = UpdateCredentialsDTO(
        blz=blz,
        username=SecureString(username) if username is not None else None,
        pin=SecureString(pin) if pin is not None else None,
        tan_method=request.tan_method,
        tan_medium=request.tan_medium,
    )

    try:
        command = UpdateCredentialsCommand.from_factory(factory)
        await command.execute(dto)
        await factory.session.commit()
        logger.info("TAN settings updated for BLZ %s", blz)
    except CredentialsNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credentials found for BLZ {blz}",
        ) from e


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
    command = DeleteCredentialsCommand.from_factory(factory)

    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )

    deleted = await command.execute(blz)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credentials found for BLZ {blz}",
        )

    await factory.session.commit()
    logger.info("Credentials deleted for BLZ %s", blz)
