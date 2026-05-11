"""Connect to a bank, fetch accounts, and import them."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from swen.application.dtos.banking import AccountInfo, ConnectionResult
from swen.domain.banking.repositories import (
    BankAccountRepository,
    BankCredentialRepository,
)
from swen.domain.banking.services.bank_fetch_service import BankFetchService
from swen.domain.banking.value_objects import (
    BankAccount,
    BankCredentials,
)
from swen.domain.integration.services import BankAccountImportService
from swen.domain.shared.time import utc_now
from swen.infrastructure.banking.bank_connection_dispatcher import (
    BankConnectionDispatcher,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class BankConnectionCommand:
    """Coordinate bank connection and account import."""

    def __init__(
        self,
        bank_fetch_service: BankFetchService,
        import_service: BankAccountImportService,
        credential_repo: BankCredentialRepository,
        bank_account_repo: Optional[BankAccountRepository] = None,
    ):
        self._bank_fetch_service = bank_fetch_service
        self._import_service = import_service
        self._credential_repo = credential_repo
        self._bank_account_repo = bank_account_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> BankConnectionCommand:
        return cls(
            bank_fetch_service=BankFetchService(
                bank_adapter=BankConnectionDispatcher.from_factory(factory)
            ),
            import_service=BankAccountImportService(
                account_repository=factory.account_repository(),
                mapping_repository=factory.account_mapping_repository(),
                current_user=factory.current_user,
            ),
            credential_repo=factory.credential_repository(),
            bank_account_repo=factory.bank_account_repository(),
        )

    async def execute(
        self,
        blz: str,
        custom_names: Optional[dict[str, str]] = None,
        bank_accounts: Optional[list[BankAccount]] = None,
    ) -> ConnectionResult:
        connected_at = utc_now()

        credentials = await self._credential_repo.find_by_blz(blz)
        credentials_were_loaded = credentials is not None
        loaded_blz = blz if credentials_were_loaded else None

        # Get accounts to import (either provided or fetched from bank)
        if bank_accounts is not None:
            accounts_to_import = bank_accounts
            bank_code = blz
        else:
            result = await self._fetch_accounts_from_bank(
                credentials=credentials,
                blz=blz,
                bank_code=blz,
                connected_at=connected_at,
            )
            if isinstance(result, ConnectionResult):
                return result  # Error occurred
            (
                accounts_to_import,
                bank_code,
                connected_at,
                fetch_credentials_were_loaded,
                fetch_loaded_blz,
            ) = result
            # If _fetch_accounts_from_bank loaded credentials, track that
            if fetch_credentials_were_loaded:
                credentials_were_loaded = True
                loaded_blz = fetch_loaded_blz

        if not accounts_to_import:
            return self._build_result(
                success=True,
                connected_at=connected_at,
                bank_code=bank_code,
                warning_message="No accounts found at bank",
            )

        return await self._import_and_build_result(
            accounts_to_import=accounts_to_import,
            custom_names=custom_names,
            connected_at=connected_at,
            bank_code=bank_code,
            credentials_were_loaded=credentials_were_loaded,
            loaded_blz=loaded_blz,
        )

    async def _fetch_accounts_from_bank(
        self,
        credentials: Optional[BankCredentials],
        blz: Optional[str],
        bank_code: str,
        connected_at,
    ) -> ConnectionResult | tuple[list[BankAccount], str, object, bool, Optional[str]]:
        credentials_were_loaded = False
        loaded_blz: Optional[str] = None

        try:
            if credentials is None:
                if blz is None:
                    msg = "blz is required when loading credentials from storage"
                    return self._build_result(
                        success=False,
                        connected_at=connected_at,
                        bank_code=bank_code,
                        error_message=msg,
                    )
                credentials = await self._load_credentials(blz)
                credentials_were_loaded = True
                loaded_blz = blz
                bank_code = blz

            tan_method, tan_medium = None, None
            if credentials_were_loaded and self._credential_repo and loaded_blz:
                tan_method, tan_medium = await self._credential_repo.get_tan_settings(
                    loaded_blz
                )

            connected_at = utc_now()
            accounts = await self._bank_fetch_service.fetch_accounts(
                credentials, tan_method=tan_method, tan_medium=tan_medium
            )

            return (
                accounts,
                credentials.blz,
                connected_at,
                credentials_were_loaded,
                loaded_blz,
            )

        except Exception as e:
            return self._build_result(
                success=False,
                connected_at=connected_at,
                bank_code=bank_code,
                error_message=str(e),
            )

    async def _import_and_build_result(  # noqa: PLR0913
        self,
        accounts_to_import: list[BankAccount],
        custom_names: Optional[dict[str, str]],
        connected_at,
        bank_code: str,
        credentials_were_loaded: bool,
        loaded_blz: Optional[str],
    ) -> ConnectionResult:
        try:
            imported_accounts = []
            for account in accounts_to_import:
                account_info = await self._import_single_account(account, custom_names)
                imported_accounts.append(account_info)

            if credentials_were_loaded and self._credential_repo and loaded_blz:
                await self._credential_repo.update_last_used(loaded_blz)

            return self._build_result(
                success=True,
                connected_at=connected_at,
                bank_code=bank_code,
                accounts_imported=imported_accounts,
            )
        except Exception as e:
            return self._build_result(
                success=False,
                connected_at=utc_now(),
                bank_code=bank_code,
                error_message=str(e),
            )

    async def _import_single_account(
        self,
        account: BankAccount,
        custom_names: Optional[dict[str, str]],
    ) -> AccountInfo:
        custom_name = custom_names.get(account.iban) if custom_names else None
        accounting_account, _mapping = await self._import_service.import_bank_account(
            account,
            custom_name=custom_name,
        )

        if self._bank_account_repo:
            await self._bank_account_repo.save(account)

        return AccountInfo(
            iban=account.iban,
            account_name=accounting_account.name,
            account_number=account.account_number,
            bank_code=account.blz,
            balance_amount=str(account.balance) if account.balance else "0.00",
            balance_currency=account.currency,
            accounting_account_id=str(accounting_account.id),
        )

    def _build_result(  # noqa: PLR0913
        self,
        success: bool,
        connected_at,
        bank_code: str,
        accounts_imported: Optional[list[AccountInfo]] = None,
        error_message: Optional[str] = None,
        warning_message: Optional[str] = None,
    ) -> ConnectionResult:
        return ConnectionResult(
            success=success,
            connected_at=connected_at,
            bank_code=bank_code,
            accounts_imported=accounts_imported or [],
            error_message=error_message,
            warning_message=warning_message,
        )

    async def _load_credentials(
        self,
        blz: str,
    ) -> BankCredentials:
        if not self._credential_repo:
            msg = (
                "Cannot load stored credentials: credential_repo not provided. "
                "Pass credential_repo to __init__ or provide credentials directly."
            )
            raise ValueError(msg)

        credentials = await self._credential_repo.find_by_blz(blz)

        if not credentials:
            msg = (
                f"No stored credentials found for BLZ {blz}. "
                f"Store credentials first using StoreCredentialsCommand."
            )
            raise ValueError(msg)

        return credentials
