"""Credentials router for bank credential management endpoints."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from swen.application.commands import StoreCredentialsCommand
from swen.application.commands.banking import BankConnectionCommand
from swen.application.queries import ListCredentialsQuery, QueryTanMethodsQuery
from swen.application.queries.integration import BankConnectionDetailsQuery
from swen.domain.banking.value_objects import BankAccount, BankCredentials
from swen.infrastructure.banking import GeldstromAdapter
from swen.infrastructure.banking.fints_institute_directory import (
    FinTSInstituteDirectoryError,
    get_fints_institute_directory_async,
)
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.credentials import (
    AccountImportInfo,
    BankAccountDetailResponse,
    BankConnectionDetailsResponse,
    BankLookupResponse,
    CredentialCreateRequest,
    CredentialCreateResponse,
    CredentialListResponse,
    CredentialResponse,
    DiscoverAccountsResponse,
    DiscoveredAccount,
    SetupBankRequest,
    SetupBankResponse,
    TANMethodQueryRequest,
    TANMethodResponse,
    TANMethodsResponse,
    TANMethodTypeStr,
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

    The credentials are encrypted before storage. Bank information (name, endpoint)
    is automatically looked up from the FinTS institute directory.

    Common TAN methods:
    - 946: SecureGo plus / Direktfreigabe (decoupled)
    - 944: SecureGo
    - 962: Smart-TAN plus manual
    - 972: chipTAN optical
    - 982: photoTAN
    """
    # Lookup bank info from institute directory
    config_repo = factory.fints_config_repository()
    try:
        directory = await get_fints_institute_directory_async(config_repo)
    except FinTSInstituteDirectoryError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    institute_info = directory.find_by_blz(request.blz)

    if institute_info is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bank with BLZ {request.blz} not found in institute directory",
        )

    # Create credentials value object
    try:
        credentials = BankCredentials.from_plain(
            blz=request.blz,
            username=request.username,
            pin=request.pin,
            endpoint=institute_info.endpoint_url,
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
            label=institute_info.name,
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
        label=institute_info.name,
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


@router.post(
    "/{blz}/discover-accounts",
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
) -> DiscoverAccountsResponse:
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

    # Load credentials
    query = ListCredentialsQuery.from_factory(factory)
    credentials = await query.find_by_bank_code(blz)

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No credentials found for BLZ {blz}",
        )

    # Load TAN settings
    tan_method, tan_medium = await query.get_tan_settings(blz)

    # Lookup bank name from institute directory
    config_repo = factory.fints_config_repository()
    try:
        directory = await get_fints_institute_directory_async(config_repo)
    except FinTSInstituteDirectoryError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    institute_info = directory.find_by_blz(blz)
    bank_name = institute_info.name if institute_info else f"Bank {blz}"

    # Connect and fetch accounts
    adapter = GeldstromAdapter(config_repository=config_repo)

    if tan_method:
        adapter.set_tan_method(tan_method)
    if tan_medium:
        adapter.set_tan_medium(tan_medium)

    try:
        await adapter.connect(credentials)
        bank_accounts = await adapter.fetch_accounts()
        await adapter.disconnect()

        logger.info(
            "Discovered %d accounts for BLZ %s",
            len(bank_accounts),
            blz,
        )

        # Return full account data for each account
        discovered = [
            DiscoveredAccount(
                iban=acc.iban,
                default_name=_generate_default_account_name(acc),
                account_number=acc.account_number,
                account_holder=acc.account_holder,
                account_type=acc.account_type,
                blz=acc.blz,
                bic=acc.bic,
                bank_name=acc.bank_name,
                currency=acc.currency,
                balance=str(acc.balance) if acc.balance else None,
                balance_date=acc.balance_date.isoformat() if acc.balance_date else None,
            )
            for acc in bank_accounts
        ]

        return DiscoverAccountsResponse(
            blz=blz,
            bank_name=bank_name,
            accounts=discovered,
        )

    except Exception as e:
        if adapter.is_connected():
            await adapter.disconnect()

        logger.exception("Account discovery failed for BLZ %s: %s", blz, e)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to bank. Please try again later.",
        ) from e


def _generate_default_account_name(bank_account) -> str:
    """
    Generate a user-friendly default account name.

    Format: "{Bank Name} - {Account Type}"
    Fallback: "{Account Holder} - {Account Type}"
    """
    if bank_account.bank_name:
        return f"{bank_account.bank_name} - {bank_account.account_type}"
    return f"{bank_account.account_holder} - {bank_account.account_type}"


@router.post(
    "/{blz}/setup",
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
    request: SetupBankRequest | None = None,
) -> SetupBankResponse:
    """
    Import discovered bank accounts.

    ## Recommended Flow (Single TAN)

    1. Call `/discover-accounts` first to connect to bank and get accounts
    2. Let user customize account names
    3. Call this endpoint with the `accounts` from step 1

    When `accounts` is provided, **no bank connection is needed** - accounts
    are imported directly, avoiding a second TAN approval.

    ## Request Body

    ```json
    {
        "accounts": [...],  // From /discover-accounts response
        "account_names": {  // Optional custom names
            "DE89...": "My Main Checking"
        }
    }
    ```

    ## Fallback (Legacy Flow)

    If `accounts` is not provided, the endpoint will connect to the bank
    to fetch accounts (requires TAN approval).

    ## TAN Handling (only if accounts not provided)

    For banks using **decoupled TAN** (e.g., SecureGo plus, pushTAN, DKB-App),
    the request will **block and wait** for you to approve in your banking app.
    """
    # Validate BLZ format
    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )

    # BankConnectionCommand handles credential loading, TAN settings, and import
    command = BankConnectionCommand.from_factory(factory)

    # Extract custom names and accounts from request if provided
    custom_names = request.account_names if request else None
    provided_accounts = None

    # Convert provided account data to BankAccount domain objects
    if request and request.accounts:
        provided_accounts = []
        for acc in request.accounts:
            balance = Decimal(acc.balance) if acc.balance else None
            balance_date = (
                datetime.fromisoformat(acc.balance_date) if acc.balance_date else None
            )
            provided_accounts.append(
                BankAccount(
                    iban=acc.iban,
                    account_number=acc.account_number,
                    account_holder=acc.account_holder,
                    account_type=acc.account_type,
                    blz=acc.blz,
                    bic=acc.bic,
                    bank_name=acc.bank_name,
                    currency=acc.currency,
                    balance=balance,
                    balance_date=balance_date,
                ),
            )

    try:
        result = await command.execute(
            blz=blz,
            custom_names=custom_names,
            bank_accounts=provided_accounts,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=result.error_message or "Bank connection failed",
        )

    # Convert to response
    accounts = [
        AccountImportInfo(
            iban=acc.iban,
            account_name=acc.account_name,
            balance=acc.balance_amount,
            currency=acc.balance_currency,
            accounting_account_id=(
                UUID(acc.accounting_account_id) if acc.accounting_account_id else None
            ),
        )
        for acc in result.accounts_imported
    ]

    logger.info(
        "Bank setup successful for BLZ %s: %d accounts imported",
        blz,
        len(accounts),
    )

    return SetupBankResponse(
        success=True,
        bank_code=blz,
        accounts_imported=accounts,
        message=f"Successfully imported {len(accounts)} bank account(s)",
        warning=result.warning_message,
    )


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
    # Lookup bank info from institute directory
    config_repo = factory.fints_config_repository()
    try:
        directory = await get_fints_institute_directory_async(config_repo)
    except FinTSInstituteDirectoryError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    institute_info = directory.find_by_blz(request.blz)

    if institute_info is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bank with BLZ {request.blz} not found in institute directory",
        )

    # Create credentials value object
    try:
        credentials = BankCredentials.from_plain(
            blz=request.blz,
            username=request.username,
            pin=request.pin,
            endpoint=institute_info.endpoint_url,
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
        result = await query.execute(credentials, institute_info.name)
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

    Returns FinTS endpoint URL and other information for a given bank code.
    Uses the Deutsche Kreditwirtschaft institute directory.
    """
    # Validate BLZ format
    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )

    config_repo = factory.fints_config_repository()
    try:
        directory = await get_fints_institute_directory_async(config_repo)
    except FinTSInstituteDirectoryError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    info = directory.find_by_blz(blz)

    if info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bank with BLZ {blz} not found in institute directory",
        )

    return BankLookupResponse(
        blz=info.blz,
        name=info.name,
        bic=info.bic,
        city=info.city,
        endpoint_url=info.endpoint_url,
    )


@router.get(
    "/{blz}/accounts",
    summary="Get bank connection details with accounts",
    responses={
        200: {"description": "Bank connection details with all accounts"},
        404: {"description": "No accounts found for this bank connection"},
    },
)
async def get_bank_connection_details(
    blz: str,
    factory: RepoFactory,
) -> BankConnectionDetailsResponse:
    """
    Get details for a bank connection including all accounts and reconciliation.

    Returns all bank accounts under this connection with:
    - Bank-reported balance (from last sync)
    - Bookkeeping balance (calculated from transactions)
    - Reconciliation status (whether they match)

    This is useful for seeing the health of a specific bank connection
    and identifying any discrepancies.
    """
    # Validate BLZ format
    if not blz.isdigit() or len(blz) != 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BLZ must be exactly 8 digits",
        )

    query = BankConnectionDetailsQuery.from_factory(factory)
    result = await query.execute(blz)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No accounts found for bank connection {blz}",
        )

    return BankConnectionDetailsResponse(
        blz=result.blz,
        bank_name=result.bank_name,
        accounts=[
            BankAccountDetailResponse(
                iban=acc.iban,
                account_name=acc.account_name,
                account_type=acc.account_type,
                currency=acc.currency,
                bank_balance=str(acc.bank_balance),
                bank_balance_date=(
                    acc.bank_balance_date.isoformat() if acc.bank_balance_date else None
                ),
                bookkeeping_balance=str(acc.bookkeeping_balance),
                discrepancy=str(acc.discrepancy),
                is_reconciled=acc.is_reconciled,
            )
            for acc in result.accounts
        ],
        total_accounts=result.total_accounts,
        reconciled_count=result.reconciled_count,
        discrepancy_count=result.discrepancy_count,
    )
