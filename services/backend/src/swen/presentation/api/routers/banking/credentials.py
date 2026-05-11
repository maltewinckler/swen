"""Credentials CRUD routers.

Has
* GET /credentials - list stored credentials (metadata only, no sensitive data)
* POST /credentials - store new credentials (with bank lookup and validation)
* DELETE /credentials/{blz} - delete credentials for a bank
"""

import logging

from fastapi import APIRouter, HTTPException, status

from swen.application.commands import DeleteCredentialsCommand, StoreCredentialsCommand
from swen.application.dtos.banking import CredentialToStoreDTO
from swen.application.queries import ListCredentialsQuery
from swen.domain.shared.value_objects import SecureString
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.banking.credentials import (
    CredentialToStore,
    StoredCredentialList,
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

    try:
        await command.execute(credential_to_store=credentials_to_store)
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Credentials stored for BLZ %s", request.blz)


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
    deleted = await command.execute(blz)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credentials found for BLZ {blz}",
        )

    await factory.session.commit()
    logger.info("Credentials deleted for BLZ %s", blz)
