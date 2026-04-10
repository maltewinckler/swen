"""Geldstrom API adapter - Anti-Corruption Layer for the Geldstrom HTTP API.

This adapter implements the BankConnectionPort by calling the Geldstrom
Banking Gateway API over HTTP. It translates between the API's JSON
responses and our domain model.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional

import httpx

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

if TYPE_CHECKING:
    from swen.infrastructure.banking.geldstrom_api.config_repository import (
        GeldstromApiConfigRepository,
    )

logger = logging.getLogger(__name__)

# Polling configuration
_MAX_POLL_DURATION_SECONDS = 300
_DEFAULT_POLL_INTERVAL_SECONDS = 5


class GeldstromApiAdapter(BankConnectionPort):
    """Anti-Corruption Layer for the Geldstrom Banking Gateway API.

    Responsibilities:
    1. Implement BankConnectionPort interface
    2. Translate Geldstrom API JSON responses to domain value objects
    3. Handle HTTP errors and translate to domain exceptions
    4. Handle async polling (202 responses) transparently
    """

    def __init__(
        self,
        config_repository: GeldstromApiConfigRepository | None = None,
    ) -> None:
        self._config_repository = config_repository
        self._client: httpx.AsyncClient | None = None
        self._credentials: BankCredentials | None = None
        self._connected: bool = False
        self._accounts_cache: list[BankAccount] | None = None
        self._preferred_tan_method: str | None = None
        self._tan_medium: str | None = None

    async def connect(self, credentials: BankCredentials) -> bool:
        """Verify credentials via the tan-methods endpoint (no 2FA triggered)."""
        try:
            logger.info(
                "Connecting to bank via Geldstrom API for BLZ %s",
                credentials.blz,
            )
            self._credentials = credentials

            client = await self._get_client()
            payload = self._build_base_payload(credentials)
            # tan-methods never requires 2FA — safe for credential verification
            await self._request_with_polling(
                client,
                "/v1/banking/tan-methods",
                payload,
                credentials,
            )

            self._connected = True
            logger.info(
                "Connected via Geldstrom API for BLZ %s.",
                credentials.blz,
            )
            return True

        except (BankAuthenticationError, BankConnectionError):
            raise
        except Exception as e:
            msg = f"Connection via Geldstrom API failed: {e}"
            raise BankConnectionError(msg) from e

    async def fetch_accounts(self) -> list[BankAccount]:
        """Fetch accounts from the API, caching the result for the session.

        May trigger 2FA for some banks. Subsequent calls return the cache.
        """
        if not self._credentials:
            msg = "Not connected. Call connect() first."
            raise BankConnectionError(msg)

        if self._accounts_cache is not None:
            return self._accounts_cache

        try:
            client = await self._get_client()
            payload = self._build_base_payload(self._credentials)
            result = await self._request_with_polling(
                client,
                "/v1/banking/accounts",
                payload,
                self._credentials,
            )

            raw_accounts = result.get("accounts", [])
            self._accounts_cache = [
                self._map_account(acc, self._credentials.blz) for acc in raw_accounts
            ]

            logger.info(
                "Fetched %d accounts via Geldstrom API.",
                len(self._accounts_cache),
            )
            return self._accounts_cache

        except (BankAuthenticationError, BankConnectionError):
            raise
        except Exception as e:
            msg = f"Failed to fetch accounts via Geldstrom API: {e}"
            raise BankConnectionError(msg) from e

    async def fetch_transactions(
        self,
        account_iban: str,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> list[BankTransaction]:
        if not self._credentials:
            msg = "Not connected. Call connect() first."
            raise BankConnectionError(msg)

        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()

        try:
            client = await self._get_client()
            payload = self._build_base_payload(self._credentials)
            payload["iban"] = account_iban
            payload["start_date"] = start_date.isoformat()
            if end_date:
                payload["end_date"] = end_date.isoformat()

            result = await self._request_with_polling(
                client,
                "/v1/banking/transactions",
                payload,
                self._credentials,
            )

            raw_txns = result.get("transactions", [])
            domain_txns = [self._map_transaction(t) for t in raw_txns]

            logger.info(
                "Fetched %d transactions for %s via Geldstrom API",
                len(domain_txns),
                account_iban,
            )
            return domain_txns

        except (BankAuthenticationError, BankConnectionError):
            raise
        except BankAccountNotFoundError:
            raise
        except Exception as e:
            msg = f"Failed to fetch transactions via Geldstrom API: {e}"
            raise BankTransactionFetchError(msg) from e

    async def disconnect(self) -> None:
        self._connected = False
        self._credentials = None
        self._accounts_cache = None
        if self._client:
            await self._client.aclose()
            self._client = None

    def is_connected(self) -> bool:
        return self._connected

    async def set_tan_callback(
        self,
        callback: Callable[[TANChallenge], Awaitable[str]],  # noqa: ARG002
    ) -> None:
        # TAN handling is managed server-side by the Geldstrom API
        logger.info("TAN callback not used in Geldstrom API mode")

    def set_tan_method(self, tan_method: str) -> None:
        self._preferred_tan_method = tan_method

    def set_tan_medium(self, tan_medium: str) -> None:
        self._tan_medium = tan_medium

    async def get_tan_methods(
        self,
        credentials: BankCredentials,
    ) -> list[TANMethod]:
        try:
            client = await self._get_client()
            payload = self._build_base_payload(credentials)

            result = await self._request_with_polling(
                client,
                "/v1/banking/tan-methods",
                payload,
                credentials,
            )

            raw_methods = result.get("methods", [])
            return [self._map_tan_method(m) for m in raw_methods]

        except (BankAuthenticationError, BankConnectionError):
            raise
        except Exception as e:
            msg = f"Failed to query TAN methods via Geldstrom API: {e}"
            raise BankConnectionError(msg) from e

    # ═══════════════════════════════════════════════════════════════
    #                   HTTP Client & Polling
    # ═══════════════════════════════════════════════════════════════

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client

        api_key, endpoint_url = await self._get_api_credentials()
        self._client = httpx.AsyncClient(
            base_url=endpoint_url.rstrip("/"),
            timeout=120.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        return self._client

    async def _request_with_polling(
        self,
        client: httpx.AsyncClient,
        path: str,
        payload: dict[str, Any],
        credentials: BankCredentials,
    ) -> dict[str, Any]:
        """Send POST request, handle 200 (immediate) or 202 (poll)."""
        try:
            response = await client.post(path, json=payload)
        except httpx.ConnectError as e:
            msg = f"Could not connect to Geldstrom API: {e}"
            raise BankConnectionError(msg) from e
        except httpx.TimeoutException as e:
            msg = f"Geldstrom API request timed out: {e}"
            raise BankConnectionError(msg) from e

        self._check_http_error(response)

        if response.status_code == 200:
            return response.json()

        if response.status_code == 202:
            return await self._poll_operation(
                client,
                response.json(),
                credentials,
            )

        msg = f"Unexpected status {response.status_code} from Geldstrom API"
        raise BankConnectionError(msg)

    async def _poll_operation(
        self,
        client: httpx.AsyncClient,
        accepted: dict[str, Any],
        credentials: BankCredentials,
    ) -> dict[str, Any]:
        """Poll an async operation until completion or timeout.

        The gateway requires bank credentials on each poll so it can
        actively resume the FinTS session to check TAN status.
        """
        operation_id = accepted["operation_id"]
        interval = accepted.get(
            "polling_interval_seconds",
            _DEFAULT_POLL_INTERVAL_SECONDS,
        )
        elapsed = 0.0
        poll_payload = self._build_base_payload(credentials)

        logger.info(
            "Operation %s pending TAN confirmation — polling...",
            operation_id,
        )

        while elapsed < _MAX_POLL_DURATION_SECONDS:
            await asyncio.sleep(interval)
            elapsed += interval

            try:
                resp = await client.post(
                    f"/v1/banking/operations/{operation_id}/poll",
                    json=poll_payload,
                )
            except httpx.HTTPError as e:
                msg = f"Polling failed: {e}"
                raise BankConnectionError(msg) from e

            # 202 = TAN still pending
            if resp.status_code == 202:
                with contextlib.suppress(Exception):
                    body = resp.json()
                    interval = body.get(
                        "polling_interval_seconds",
                        interval,
                    )
                continue

            self._check_http_error(resp)
            data = resp.json()
            status = data.get("status")

            if status == "completed":
                logger.info(
                    "Operation %s completed.",
                    operation_id,
                )
                return data

            if status == "failed":
                reason = data.get("failure_reason", "Unknown error")
                self._raise_for_failure(reason)

        msg = (
            f"Geldstrom API operation {operation_id} timed out "
            f"after {_MAX_POLL_DURATION_SECONDS}s"
        )
        raise BankConnectionError(msg)

    def _check_http_error(self, response: httpx.Response) -> None:
        """Translate HTTP errors to domain exceptions."""
        if response.is_success or response.status_code == 202:
            return

        status = response.status_code

        if status in (401, 403):
            msg = f"Authentication failed (HTTP {status})"
            raise BankAuthenticationError(msg)

        if status == 422:
            detail = self._extract_error_detail(response)
            msg = f"Validation error: {detail}"
            raise BankConnectionError(msg)

        detail = self._extract_error_detail(response)
        msg = f"Geldstrom API error (HTTP {status}): {detail}"
        raise BankConnectionError(msg)

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        with contextlib.suppress(Exception):
            body = response.json()
            if "detail" in body:
                detail = body["detail"]
                if isinstance(detail, list):
                    return "; ".join(d.get("msg", str(d)) for d in detail)
                return str(detail)
        return response.text[:200] if response.text else "No details"

    @staticmethod
    def _raise_for_failure(reason: str) -> None:
        lower = reason.lower()
        if "authentication" in lower or "pin" in lower:
            raise BankAuthenticationError(reason)
        raise BankConnectionError(reason)

    # ═══════════════════════════════════════════════════════════════
    #               Payload Building & Credential Resolution
    # ═══════════════════════════════════════════════════════════════

    def _build_base_payload(
        self,
        credentials: BankCredentials,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "protocol": "fints",
            "blz": credentials.blz,
            "user_id": credentials.username.get_value(),
            "password": credentials.pin.get_value(),
        }
        if self._preferred_tan_method:
            payload["tan_method"] = self._preferred_tan_method
        if self._tan_medium:
            payload["tan_medium"] = self._tan_medium
        return payload

    async def _get_api_credentials(self) -> tuple[str, str]:
        """Get API key and endpoint URL from config repository."""
        if not self._config_repository:
            msg = (
                "Geldstrom API configuration repository not available. "
                "Cannot connect without configuration."
            )
            raise BankConnectionError(msg)

        config = await self._config_repository.get_configuration()
        if not config or not config.api_key:
            msg = (
                "Geldstrom API key not configured. "
                "An administrator must configure the API key."
            )
            raise BankConnectionError(msg)

        return config.api_key, config.endpoint_url

    # ═══════════════════════════════════════════════════════════════
    #              Response Mapping → Domain Value Objects
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _map_account(
        data: dict[str, Any],
        blz: str,
    ) -> BankAccount:
        iban = data.get("iban", "")
        balance = None
        raw_balance = data.get("balance")
        if raw_balance is not None:
            with contextlib.suppress(Exception):
                balance = Decimal(str(raw_balance))

        balance_date = None
        raw_bd = data.get("balance_date")
        if raw_bd:
            with contextlib.suppress(Exception):
                balance_date = datetime.fromisoformat(str(raw_bd))

        return BankAccount(
            iban=iban or f"UNKNOWN-{blz}",
            account_number=data.get("account_number", iban[:10] if iban else ""),
            blz=data.get("blz", blz),
            account_holder=data.get("owner", "Unknown"),
            account_type=data.get("product_name", "Unknown Account Type"),
            currency=data.get("currency", "EUR"),
            bic=data.get("bic"),
            bank_name=data.get("bank_name"),
            balance=balance,
            balance_date=balance_date,
        )

    @staticmethod
    def _map_transaction(data: dict[str, Any]) -> BankTransaction:
        return BankTransaction(
            booking_date=date.fromisoformat(str(data["booking_date"])),
            value_date=date.fromisoformat(str(data["value_date"])),
            amount=Decimal(str(data["amount"])),
            currency=data.get("currency", "EUR"),
            purpose=data.get("purpose", "No description"),
            applicant_name=data.get("counterpart_name"),
            applicant_iban=data.get("counterpart_iban"),
            applicant_bic=data.get("bic"),
            bank_reference=data.get("entry_id"),
            customer_reference=data.get("customer_reference"),
            end_to_end_reference=data.get("end_to_end_reference"),
            mandate_reference=data.get("mandate_reference"),
            creditor_id=data.get("creditor_id"),
            transaction_code=data.get("transaction_code"),
            posting_text=data.get("posting_text"),
        )

    @staticmethod
    def _map_tan_method(data: dict[str, Any]) -> TANMethod:
        # API returns method_id/display_name; fall back to code/name
        code = data.get("method_id") or data.get("code", "")
        name = data.get("display_name") or data.get("name", "")

        # Infer decoupled from well-known codes (946 = SecureGo plus, 910 = pushTAN)
        is_decoupled = data.get("is_decoupled", False)
        if not is_decoupled and code in ("910", "944", "946"):
            is_decoupled = True

        try:
            method_type = TANMethodType(data.get("method_type", "unknown"))
        except ValueError:
            method_type = TANMethodType.UNKNOWN

        return TANMethod(
            code=code,
            name=name,
            method_type=method_type,
            is_decoupled=is_decoupled,
            technical_id=data.get("technical_id"),
            zka_id=data.get("zka_id"),
            zka_version=data.get("zka_version"),
            max_tan_length=data.get("max_tan_length"),
            decoupled_max_polls=data.get("decoupled_max_polls"),
            decoupled_first_poll_delay=data.get("decoupled_first_poll_delay"),
            decoupled_poll_interval=data.get("decoupled_poll_interval"),
            supports_cancel=data.get("supports_cancel", False),
            supports_multiple_tan=data.get("supports_multiple_tan", False),
        )
