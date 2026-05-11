"""Bank Discovery Routers."""

import logging
from typing import cast

from fastapi import APIRouter, HTTPException, status

from swen.application.commands.banking import (
    DiscoverAccountsCommand,
)
from swen.application.queries import QueryTanMethodsQuery
from swen.application.queries.banking import LookupBankQuery
from swen.domain.banking.value_objects import BankCredentials
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.credentials import (
    BankDiscoveryResult,
    BankLookupResponse,
    TANMethodQueryRequest,
    TANMethodResponse,
    TANMethodsResponse,
    TANMethodTypeStr,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/lookup/{blz}",
    summary="Lookup bank information",
    responses={
        200: {"description": "Bank information"},
        400: {"description": "Invalid BLZ format"},
        404: {"description": "Bank not found"},
    },
)
async def lookup_bank(
    blz: str,
    factory: RepoFactory,
) -> BankLookupResponse:
    """
    Lookup bank information by BLZ.

    Returns bank metadata for a given bank code.
    """
    # Validate BLZ format
    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )

    lookup = LookupBankQuery.from_factory(factory)
    info = await lookup.execute(blz)

    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bank with BLZ {blz} not found in bank directory",
        )

    return BankLookupResponse(
        blz=info.blz,
        name=info.name,
        bic=info.bic,
        organization=info.organization,
        is_fints_capable=info.is_fints_capable,
    )


@router.post(
    "/discover/{blz}",
    summary="Discover bank accounts without importing",
    responses={
        200: {"description": "Bank accounts discovered successfully"},
        400: {"description": "Invalid BLZ format"},
        404: {"description": "Credentials not found"},
        503: {"description": "Connection failed"},
        504: {"description": "TAN approval timeout"},
    },
)
async def discover_bank_accounts(
    blz: str,
    factory: RepoFactory,
) -> BankDiscoveryResult:
    """
    Connect to bank and discover accounts without importing them.

    This endpoint is useful for previewing which accounts will be imported
    and allowing the user to customize account names before actual import.

    This endpoint:
    1. Connects to the bank using stored credentials
    2. Fetches all available bank accounts
    3. Returns the list of discovered accounts with default names
    4. Does NOT create any accounting accounts or mappings

    Use this before calling the /setup endpoint to let users customize
    account names.

    ## TAN Handling

    For banks using **decoupled TAN** (e.g., SecureGo plus, pushTAN, DKB-App),
    the request will **block and wait** for you to approve in your banking app:

    - Maximum wait time: **5 minutes**
    - Approve the connection in your banking app when prompted

    **Important:** Set your HTTP client timeout to at least 6 minutes.
    """
    # Validate BLZ format
    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )

    try:
        command = DiscoverAccountsCommand.from_factory(factory)
        dto = await command.execute(blz)
        return BankDiscoveryResult(**dto.model_dump())

    except Exception as e:
        logger.exception("Account discovery failed for BLZ %s: %s", blz, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to bank. Please try again later.",
        ) from e


@router.post(
    "/tan-methods",
    summary="Query available TAN methods",
    responses={
        200: {"description": "Available TAN methods"},
        400: {"description": "Invalid input or bank not found"},
        401: {"description": "Invalid credentials"},
        503: {"description": "Bank connection failed"},
    },
)
async def query_tan_methods(
    request: TANMethodQueryRequest,
    factory: RepoFactory,
) -> TANMethodsResponse:
    """
    Query available TAN methods from the bank.

    This performs a lightweight sync dialog to discover which TAN authentication
    methods are supported for the user. This does NOT require TAN approval,
    making it safe to call before choosing a TAN method.

    Use this endpoint during credential setup to:
    1. Validate that credentials work
    2. Discover available TAN methods
    3. Let the user choose their preferred method

    Common TAN method types:
    - **decoupled**: App-based approval (e.g., DKB App, SecureGo plus) - recommended
    - **chiptan**: Hardware token with flickering barcode or USB
    - **photo_tan**: QR code scanning
    - **sms**: SMS-based TAN
    - **manual**: Manual code entry
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

    # Query TAN methods using application query
    query = QueryTanMethodsQuery.from_factory(factory)

    try:
        result = await query.execute(credentials, bank_info.name)
    except Exception as e:
        error_msg = str(e).lower()
        if "authentication" in error_msg or "pin" in error_msg:
            logger.warning("Authentication failed for BLZ %s: %s", request.blz, e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials - please check username and PIN",
            ) from e
        logger.exception("Failed to query TAN methods for BLZ %s: %s", request.blz, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to bank. Please try again later.",
        ) from e

    # Map to response
    return TANMethodsResponse(
        blz=result.blz,
        bank_name=result.bank_name,
        tan_methods=[
            TANMethodResponse(
                code=m.code,
                name=m.name,
                method_type=cast(TANMethodTypeStr, m.method_type),
                is_decoupled=m.is_decoupled,
                technical_id=m.technical_id,
                zka_id=m.zka_id,
                zka_version=m.zka_version,
                max_tan_length=m.max_tan_length,
                decoupled_max_polls=m.decoupled_max_polls,
                decoupled_first_poll_delay=m.decoupled_first_poll_delay,
                decoupled_poll_interval=m.decoupled_poll_interval,
                supports_cancel=m.supports_cancel,
                supports_multiple_tan=m.supports_multiple_tan,
            )
            for m in result.tan_methods
        ],
        default_method=result.default_method,
    )
