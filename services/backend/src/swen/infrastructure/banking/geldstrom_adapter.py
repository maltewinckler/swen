"""Geldstrom adapter - Anti-Corruption Layer for geldstrom FinTS client.

This adapter implements the BankConnectionPort using the geldstrom library.
It translates between geldstrom's data structures and our domain model.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Awaitable, Callable

from geldstrom import FinTS3Client
from geldstrom.domain import (
    Account,
    TANConfig,
    TransactionEntry,
)
from geldstrom.domain import TANMethod as GeldstromTANMethod

from swen.domain.banking.exceptions import (
    BankAccountNotFoundError,
    BankAuthenticationError,
    BankConnectionError,
    BankTransactionFetchError,
)
from swen.domain.banking.ports.bank_connection_port import BankConnectionPort
from swen.domain.banking.value_objects.bank_account import BankAccount
from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.domain.banking.value_objects.bank_transaction import BankTransaction
from swen.domain.banking.value_objects.tan_challenge import TANChallenge
from swen.domain.banking.value_objects.tan_method import (
    TANMethod,
    TANMethodType,
)
from swen.domain.shared.time import utc_now

if TYPE_CHECKING:
    from collections.abc import Sequence

from swen_config.settings import get_settings

logger = logging.getLogger(__name__)


class GeldstromAdapter(BankConnectionPort):
    """
    Geldstrom Adapter - Anti-Corruption Layer.

    This adapter wraps the geldstrom library and translates
    between geldstrom-specific concepts and our domain model.

    Responsibilities:
    1. Implement BankConnectionPort interface
    2. Translate geldstrom data structures to domain value objects
    3. Handle geldstrom-specific errors and convert to domain exceptions
    4. Manage geldstrom client lifecycle
    """

    def __init__(self) -> None:
        self._client: FinTS3Client | None = None
        self._credentials: BankCredentials | None = None
        self._accounts_cache: list[BankAccount] | None = None
        self._geldstrom_accounts_cache: Sequence[Account] | None = None
        self._preferred_tan_method: str | None = None
        self._tan_medium: str | None = None

    async def connect(self, credentials: BankCredentials) -> bool:
        try:
            logger.info(
                "Connecting to bank with BLZ %s at %s",
                credentials.blz,
                credentials.endpoint,
            )

            if self._preferred_tan_method:
                logger.info("Using TAN method: %s", self._preferred_tan_method)
            if self._tan_medium:
                logger.info("Using TAN medium: %s", self._tan_medium)

            # Create geldstrom client with challenge handler
            settings = get_settings()
            self._client = FinTS3Client(
                bank_code=credentials.blz,
                server_url=credentials.endpoint,
                user_id=credentials.username.get_value(),
                pin=credentials.pin.get_value(),
                product_id=settings.fints_product_id,
                tan_method=self._preferred_tan_method,
                tan_medium=self._tan_medium,
                tan_config=TANConfig(
                    poll_interval=5.0,
                    timeout_seconds=300.0,  # 5 minutes for decoupled TAN
                ),
            )

            self._credentials = credentials

            # Connect and fetch accounts (geldstrom is synchronous)
            geldstrom_accounts = self._client.connect()

            # Cache geldstrom accounts for later lookup
            self._geldstrom_accounts_cache = geldstrom_accounts

            # Transform to domain model
            self._accounts_cache = await self._map_accounts_to_domain(
                geldstrom_accounts,
            )

            logger.info(
                "Successfully connected to bank. Found %d accounts.",
                len(self._accounts_cache),
            )

            return True

        except Exception as e:
            error_msg = str(e)
            logger.error("Connection failed: %s", error_msg)

            # Translate errors to domain exceptions
            if "authentication" in error_msg.lower() or "pin" in error_msg.lower():
                msg = f"Authentication failed: {error_msg}"
                raise BankAuthenticationError(msg) from e

            msg = f"Connection failed: {error_msg}"
            raise BankConnectionError(msg) from e

    async def fetch_accounts(self) -> list[BankAccount]:
        if not self._client:
            msg = "Not connected to bank. Call connect() first."
            raise BankConnectionError(msg)

        # Return cached accounts if available
        if self._accounts_cache is not None:
            return self._accounts_cache

        try:
            logger.info("Fetching accounts from bank...")

            # Fetch accounts from geldstrom
            geldstrom_accounts = self._client.list_accounts()
            self._geldstrom_accounts_cache = geldstrom_accounts

            # Transform to domain model
            domain_accounts = await self._map_accounts_to_domain(geldstrom_accounts)
            self._accounts_cache = domain_accounts

            logger.info("Successfully fetched %d accounts", len(domain_accounts))

            return domain_accounts

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to fetch accounts: %s", error_msg)
            msg = f"Failed to fetch accounts: {error_msg}"
            raise BankConnectionError(msg) from e

    async def fetch_transactions(
        self,
        account_iban: str,
        start_date: date | datetime,
        end_date: date | datetime | None = None,
    ) -> list[BankTransaction]:
        if not self._client:
            msg = "Not connected to bank. Call connect() first."
            raise BankConnectionError(msg)

        # Convert datetime to date if needed (geldstrom requires date objects)
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()

        if end_date is None:
            end_date = utc_now().date()

        try:
            logger.info(
                "Fetching transactions for IBAN %s from %s to %s",
                account_iban,
                start_date,
                end_date,
            )

            # Find the geldstrom account by IBAN
            geldstrom_account = self._find_geldstrom_account(account_iban)

            if not geldstrom_account:
                msg = f"Account with IBAN {account_iban} not found"
                raise BankAccountNotFoundError(msg)

            # Fetch transactions from geldstrom
            # TAN handling is automatic via challenge_handler
            feed = self._client.get_transactions(
                geldstrom_account,
                start_date=start_date,
                end_date=end_date,
            )

            # Transform to domain model
            domain_transactions = self._map_transactions_to_domain(feed.entries)

            logger.info(
                "Successfully fetched %d transactions",
                len(domain_transactions),
            )

            return domain_transactions

        except BankAccountNotFoundError:
            raise

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to fetch transactions: %s", error_msg)
            msg = f"Failed to fetch transactions: {error_msg}"
            raise BankTransactionFetchError(msg) from e

    async def disconnect(self) -> None:
        """Close the bank connection."""
        if self._client:
            logger.info("Disconnecting from bank")
            self._client.disconnect()
            self._client = None
            self._credentials = None
            self._accounts_cache = None
            self._geldstrom_accounts_cache = None

    def is_connected(self) -> bool:
        """Check if currently connected to bank."""
        return self._client is not None and self._client.is_connected

    async def set_tan_callback(
        self,
        callback: Callable[[TANChallenge], Awaitable[str]],  # NOQA: ARG002
    ):
        logger.info("TAN setting callback not implemented so far")

    def set_tan_method(self, tan_method: str):
        self._preferred_tan_method = tan_method
        logger.info("Preferred TAN method set to: %s", tan_method)

    def set_tan_medium(self, tan_medium: str):
        self._tan_medium = tan_medium
        logger.info("TAN medium set to: %s", tan_medium)

    async def get_tan_methods(
        self,
        credentials: BankCredentials,
    ) -> list[TANMethod]:
        try:
            logger.info(
                "Querying TAN methods for BLZ %s at %s",
                credentials.blz,
                credentials.endpoint,
            )

            # Create a temporary client to query TAN methods
            settings = get_settings()
            client = FinTS3Client(
                bank_code=credentials.blz,
                server_url=credentials.endpoint,
                user_id=credentials.username.get_value(),
                pin=credentials.pin.get_value(),
                product_id=settings.fints_product_id,
            )

            # Query TAN methods (uses sync dialog, no TAN needed)
            geldstrom_methods = client.get_tan_methods()

            # Map to domain model
            domain_methods = [self._map_tan_method(m) for m in geldstrom_methods]

            logger.info(
                "Found %d TAN method(s) for BLZ %s",
                len(domain_methods),
                credentials.blz,
            )

            return domain_methods

        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to query TAN methods: %s", error_msg)

            if "authentication" in error_msg.lower() or "pin" in error_msg.lower():
                msg = f"Authentication failed: {error_msg}"
                raise BankAuthenticationError(msg) from e

            msg = f"Failed to query TAN methods: {error_msg}"
            raise BankConnectionError(msg) from e

    def _map_tan_method(self, geldstrom_method: GeldstromTANMethod) -> TANMethod:
        # Map the method type enum
        try:
            method_type = TANMethodType(geldstrom_method.method_type.value)
        except ValueError:
            method_type = TANMethodType.UNKNOWN

        return TANMethod(
            code=geldstrom_method.code,
            name=geldstrom_method.name,
            method_type=method_type,
            is_decoupled=geldstrom_method.is_decoupled,
            technical_id=geldstrom_method.technical_id,
            zka_id=geldstrom_method.zka_id,
            zka_version=geldstrom_method.zka_version,
            max_tan_length=geldstrom_method.max_tan_length,
            decoupled_max_polls=geldstrom_method.decoupled_max_polls,
            decoupled_first_poll_delay=geldstrom_method.decoupled_first_poll_delay,
            decoupled_poll_interval=geldstrom_method.decoupled_poll_interval,
            supports_cancel=geldstrom_method.supports_cancel,
            supports_multiple_tan=geldstrom_method.supports_multiple_tan,
        )

    async def _map_accounts_to_domain(
        self,
        geldstrom_accounts: Sequence[Account],
    ) -> list[BankAccount]:
        domain_accounts = []

        for account in geldstrom_accounts:
            try:
                # Fetch balance for this account
                balance = None
                balance_date = None
                if (
                    self._client
                    and account.capabilities
                    and account.capabilities.can_fetch_balance
                ):
                    try:
                        snapshot = self._client.get_balance(account)
                        balance = snapshot.booked.amount
                        balance_date = snapshot.as_of
                    except Exception as e:
                        logger.warning(
                            "Could not fetch balance for %s: %s",
                            account.iban,
                            e,
                        )

                domain_account = self._map_account_to_domain(
                    account,
                    balance,
                    balance_date,
                )
                domain_accounts.append(domain_account)

            except Exception as e:  # NOQA: PERF203
                logger.warning(
                    "Failed to map account %s: %s. Skipping.",
                    account.account_id,
                    e,
                )
                continue

        return domain_accounts

    def _map_account_to_domain(
        self,
        account: Account,
        balance: Decimal | None = None,
        balance_date: datetime | None = None,
    ) -> BankAccount:
        # Parse account_id to extract account_number
        # Format: "account_number:subaccount"  # NOQA: ERA001
        account_number = account.account_id.split(":")[0]

        # Extract account holder from owner
        account_holder = "Unknown"
        if account.owner:
            account_holder = account.owner.name

        # Get bank code from route
        blz = account.bank_route.bank_code

        # BIC validation - ensure it's valid length
        bic = account.bic
        if bic and len(bic) > 11:
            bic = None

        return BankAccount(
            iban=account.iban or f"UNKNOWN{account.account_id}",
            account_number=account_number,
            blz=blz,
            account_holder=account_holder,
            account_type=account.product_name or "Unknown Account Type",
            currency=account.currency or "EUR",
            bic=bic,
            bank_name=None,  # Not available in geldstrom
            balance=balance,
            balance_date=balance_date,
        )

    def _map_transactions_to_domain(
        self,
        entries: Sequence[TransactionEntry],
    ) -> list[BankTransaction]:
        domain_transactions = []

        for entry in entries:
            try:
                domain_tx = self._map_transaction_to_domain(entry)
                domain_transactions.append(domain_tx)
            except Exception as e:  # NOQA: PERF203
                logger.warning(
                    "Failed to map transaction %s: %s. Skipping.",
                    entry.entry_id,
                    e,
                )
                continue

        return domain_transactions

    def _map_transaction_to_domain(
        self,
        entry: TransactionEntry,
    ) -> BankTransaction:
        # Extract optional fields from metadata
        metadata = dict(entry.metadata) if entry.metadata else {}

        return BankTransaction(
            booking_date=entry.booking_date,
            value_date=entry.value_date,
            amount=entry.amount,
            currency=entry.currency,
            purpose=entry.purpose or "No description",
            applicant_name=entry.counterpart_name,
            applicant_iban=entry.counterpart_iban,
            applicant_bic=metadata.get("bic"),
            bank_reference=entry.entry_id,
            customer_reference=metadata.get("customer_reference"),
            end_to_end_reference=metadata.get("end_to_end_reference"),
            mandate_reference=metadata.get("mandate_reference"),
            creditor_id=metadata.get("creditor_id"),
            transaction_code=metadata.get("transaction_code"),
            posting_text=metadata.get("posting_text"),
        )

    def _find_geldstrom_account(self, iban: str) -> Account | None:
        if not self._geldstrom_accounts_cache:
            return None

        for account in self._geldstrom_accounts_cache:
            if account.iban == iban:
                return account

        return None
