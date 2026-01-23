"""HTTP client for the ML classification service."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, AsyncIterator, Set

import httpx
from swen_ml_contracts import (
    ClassifyBatchRequest,
    ClassifyBatchResponse,
    EmbedAccountsRequest,
    EmbedAccountsResponse,
    HealthResponse,
    StoreExampleRequest,
    StoreExampleResponse,
)

if TYPE_CHECKING:
    from uuid import UUID

    from swen_ml_contracts import AccountOption, TransactionInput

logger = logging.getLogger(__name__)

# Store references to fire-and-forget tasks to prevent garbage collection
_background_tasks: Set[asyncio.Task] = set()


class MLServiceClient:
    """HTTP client wrapper for the ML service API."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,  # Increased for batch operations
        enabled: bool = True,
    ):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._enabled = enabled
        self._client: httpx.AsyncClient | None = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> HealthResponse | None:
        """Check if the ML service is healthy."""
        if not self._enabled:
            return None
        try:
            client = await self._get_client()
            response = await client.get("/health")
            response.raise_for_status()
            return HealthResponse.model_validate(response.json())
        except Exception as e:
            logger.warning("ML service health check failed: %s", e)
            return None

    # -------------------------------------------------------------------------
    # Batch Classification (Primary API)
    # -------------------------------------------------------------------------

    async def classify_batch(
        self,
        user_id: UUID,
        transactions: list[TransactionInput],
        available_accounts: list[AccountOption],
    ) -> ClassifyBatchResponse | None:
        """Classify a batch of transactions."""
        if not self._enabled:
            return None
        try:
            request = ClassifyBatchRequest(
                user_id=user_id,
                transactions=transactions,
                available_accounts=available_accounts,
            )
            client = await self._get_client()
            response = await client.post(
                "/classify/batch",
                content=request.model_dump_json(),
            )
            response.raise_for_status()
            return ClassifyBatchResponse.model_validate(response.json())
        except Exception as e:
            logger.warning("ML batch classification failed: %s", e)
            return None

    async def classify_batch_streaming(
        self,
        user_id: UUID,
        transactions: list[TransactionInput],
        available_accounts: list[AccountOption],
    ) -> AsyncIterator[dict]:
        """Classify batch with SSE streaming for progress updates.

        Yields dicts with either:
        - Progress: {"type": "progress", "current": N, "total": M, ...}
        - Result: {"type": "result", "classifications": [...], ...}
        """
        if not self._enabled:
            return

        request = ClassifyBatchRequest(
            user_id=user_id,
            transactions=transactions,
            available_accounts=available_accounts,
        )

        try:
            # Use streaming request for SSE
            async with (
                httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=httpx.Timeout(timeout=120.0, connect=10.0),
                ) as client,
                client.stream(
                    "POST",
                    "/classify/batch/stream",
                    content=request.model_dump_json(),
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "text/event-stream",
                    },
                ) as response,
            ):
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data_str = line[5:].strip()  # Remove "data:" prefix
                    if not data_str:
                        continue

                    try:
                        data = json.loads(data_str)
                        yield data
                    except json.JSONDecodeError:
                        logger.warning("Invalid SSE data: %s", data_str)
                        continue

        except Exception as e:
            logger.warning("ML batch classification streaming failed: %s", e)

    # -------------------------------------------------------------------------
    # Example Storage (Learning)
    # -------------------------------------------------------------------------

    async def store_example(
        self,
        user_id: UUID,
        request: StoreExampleRequest,
    ) -> StoreExampleResponse | None:
        """Store a posted transaction as a training example."""
        if not self._enabled:
            return None
        try:
            client = await self._get_client()
            response = await client.post(
                f"/users/{user_id}/examples",
                content=request.model_dump_json(),
            )
            response.raise_for_status()
            return StoreExampleResponse.model_validate(response.json())
        except Exception as e:
            logger.warning("ML store example failed: %s", e)
            return None

    def store_example_fire_and_forget(
        self,
        user_id: UUID,
        request: StoreExampleRequest,
    ) -> None:
        """Store example without waiting for response (fire-and-forget)."""
        if not self._enabled:
            logger.debug("ML service disabled, skipping store_example")
            return

        logger.debug(
            "Storing example for user=%s, account=%s (fire-and-forget)",
            user_id,
            request.account_number,
        )

        async def _store():
            try:
                result = await self.store_example(user_id, request)
                if result:
                    logger.debug(
                        "Example stored: user=%s, total=%d",
                        user_id,
                        result.total_examples,
                    )
            except Exception as e:
                logger.warning("Fire-and-forget store example failed: %s", e)

        task = asyncio.create_task(_store())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    # -------------------------------------------------------------------------
    # Account Embeddings (Anchors)
    # -------------------------------------------------------------------------

    async def embed_accounts(
        self,
        user_id: UUID,
        accounts: list[AccountOption],
    ) -> EmbedAccountsResponse | None:
        """Compute and store anchor embeddings for accounts."""
        if not self._enabled:
            return None
        try:
            request = EmbedAccountsRequest(
                user_id=user_id,
                accounts=accounts,
            )
            client = await self._get_client()
            response = await client.post(
                f"/users/{user_id}/accounts/embed",
                content=request.model_dump_json(),
            )
            response.raise_for_status()
            return EmbedAccountsResponse.model_validate(response.json())
        except Exception as e:
            logger.warning("ML embed accounts failed: %s", e)
            return None

    def embed_accounts_fire_and_forget(
        self,
        user_id: UUID,
        accounts: list[AccountOption],
    ) -> None:
        """Embed accounts without waiting for response (fire-and-forget)."""
        if not self._enabled:
            logger.debug("ML service disabled, skipping embed_accounts")
            return

        logger.debug(
            "Embedding %d accounts for user=%s (fire-and-forget)",
            len(accounts),
            user_id,
        )

        async def _embed():
            try:
                result = await self.embed_accounts(user_id, accounts)
                if result:
                    logger.debug(
                        "Accounts embedded: user=%s, count=%d",
                        user_id,
                        result.embedded,
                    )
            except Exception as e:
                logger.warning("Fire-and-forget embed accounts failed: %s", e)

        task = asyncio.create_task(_embed())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
