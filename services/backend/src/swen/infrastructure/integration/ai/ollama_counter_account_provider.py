"""Ollama-based AI provider for counter-account resolution.

This module implements the AICounterAccountProvider interface using Ollama,
a self-hosted LLM runtime. It supports various models optimized for German
personal finance transaction classification.

Recommended models (in order of size/quality):
- qwen2.5:1.5b  (1GB)  - Fast, good quality, MVP default
- qwen2.5:3b    (2GB)  - Better accuracy
- llama3.2:3b   (2GB)  - Alternative with good multilingual support
- mistral:7b    (4GB)  - Best accuracy for complex cases
"""

import json
import logging
import re
from typing import Optional

import httpx

from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.services import AICounterAccountProvider
from swen.domain.integration.value_objects import (
    AICounterAccountResult,
    CounterAccountOption,
)

logger = logging.getLogger(__name__)


class OllamaCounterAccountProvider(AICounterAccountProvider):
    """
    AI Counter-Account provider using Ollama for self-hosted LLM inference.

    This provider sends bank transaction data to a local Ollama instance
    and parses the LLM's response to determine the best counter-account.
    """

    # Default prompt template for transaction classification
    # English instructions work better with small models, even for German data
    DEFAULT_PROMPT_TEMPLATE = """You are a personal finance assistant classifying German bank transactions.

TRANSACTION:
- Purpose: {purpose}
- Amount: {amount} EUR ({direction})
- Counterparty: {counterparty}
- Date: {booking_date}

AVAILABLE ACCOUNTS (with descriptions showing typical transactions):
{accounts_list}

TASK: Select the most appropriate account for this transaction.
Use the descriptions to match merchants/keywords (e.g., "REWE" → Groceries, "Netflix" → Streaming).

Respond with ONLY this JSON format, no additional text:
{{"account_number": "XXXX", "confidence": 0.X, "reason": "Brief explanation"}}

- account_number: The account number that best matches (e.g., "4000")
- confidence: Your certainty from 0.0 to 1.0 (use LOW confidence if no description matches)
- reason: Brief explanation (1 sentence)

IMPORTANT: If the transaction doesn't clearly match any account description, use "4900" (Other/Miscellaneous) with confidence < 0.5.
"""  # NOQA: E501

    def __init__(
        self,
        model: str = "qwen2.5:1.5b",
        base_url: str = "http://localhost:11434",
        min_confidence: float = 0.7,
        timeout: float = 30.0,
        prompt_template: Optional[str] = None,
    ):
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._min_confidence = min_confidence
        self._timeout = timeout
        self._prompt_template = prompt_template or self.DEFAULT_PROMPT_TEMPLATE

    @property
    def min_confidence_threshold(self) -> float:
        return self._min_confidence

    @property
    def model_name(self) -> str:
        return self._model

    async def resolve(
        self,
        transaction: BankTransaction,
        available_accounts: list[CounterAccountOption],
    ) -> Optional[AICounterAccountResult]:
        if not available_accounts:
            logger.warning("No available accounts provided for AI resolution")
            return None

        try:
            return await self._resolve_with_ollama(transaction, available_accounts)
        except Exception as e:
            self._log_resolution_error(e)
            return None

    async def _resolve_with_ollama(
        self,
        transaction: BankTransaction,
        available_accounts: list[CounterAccountOption],
    ) -> Optional[AICounterAccountResult]:
        prompt = self._build_prompt(transaction, available_accounts)
        logger.debug("AI Prompt:\n%s", prompt)

        response_text = await self._call_ollama(prompt)
        if not response_text:
            return None

        logger.debug("AI Response: %s", response_text)
        return self._parse_response(response_text, available_accounts)

    def _log_resolution_error(self, e: Exception) -> None:
        if isinstance(e, httpx.TimeoutException):
            logger.warning("Ollama request timed out after %.1fs", self._timeout)
        elif isinstance(e, httpx.ConnectError):
            logger.warning(
                "Could not connect to Ollama at %s. Is it running?",
                self._base_url,
            )
        elif isinstance(e, httpx.ReadError):
            logger.warning(
                "Connection to Ollama was interrupted while reading response. "
                "The model may still be loading. Try again in a few seconds.",
            )
        else:
            logger.warning(
                "AI resolution failed: %s (type: %s)",
                str(e) or repr(e),
                type(e).__name__,
            )

    def _build_prompt(
        self,
        transaction: BankTransaction,
        accounts: list[CounterAccountOption],
    ) -> str:
        # Determine transaction direction
        direction = "expense/outgoing" if transaction.is_debit() else "income/incoming"

        # Format accounts list with descriptions when available
        accounts_list = "\n".join(self._format_account_option(acc) for acc in accounts)

        # Build prompt from template
        return self._prompt_template.format(
            purpose=transaction.purpose or "(not provided)",
            amount=abs(transaction.amount),
            direction=direction,
            counterparty=transaction.applicant_name or "Unknown",
            booking_date=transaction.booking_date.strftime("%d.%m.%Y"),
            accounts_list=accounts_list,
        )

    def _format_account_option(self, account: CounterAccountOption) -> str:
        base = f"- [{account.account_number}] {account.name} ({account.account_type})"
        if account.description:
            return f"{base}: {account.description}"
        return base

    async def _call_ollama(self, prompt: str) -> Optional[str]:
        url = f"{self._base_url}/api/generate"

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temperature for consistent output
                "num_predict": 200,  # Limit response length
            },
        }

        # Allow extra time for model loading (cold start)
        timeout = httpx.Timeout(connect=5.0, read=self._timeout, write=10.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            return data.get("response", "")

    def _parse_response(
        self,
        response_text: str,
        available_accounts: list[CounterAccountOption],
    ) -> Optional[AICounterAccountResult]:
        # Build lookup for account validation
        account_by_number = {acc.account_number: acc for acc in available_accounts}

        # Try to extract JSON from response
        json_data = self._extract_json(response_text)

        if json_data:
            return self._parse_json_response(json_data, account_by_number)

        # Fallback: try to extract just the account number
        return self._parse_simple_response(response_text, account_by_number)

    def _extract_json(self, text: str) -> Optional[dict]:
        # Try to find JSON in code blocks first
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find raw JSON object
        json_match = re.search(r"\{[^{}]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _parse_json_response(
        self,
        json_data: dict,
        account_by_number: dict[str, CounterAccountOption],
    ) -> Optional[AICounterAccountResult]:
        account_number = str(json_data.get("account_number", ""))
        confidence = float(json_data.get("confidence", 0.5))
        reasoning = json_data.get("reason") or json_data.get("reasoning")

        # Validate account exists
        account = account_by_number.get(account_number)
        if not account:
            logger.debug(
                "AI suggested invalid account number: %s",
                account_number,
            )
            return None

        # Clamp confidence to valid range
        confidence = max(0.0, min(1.0, confidence))

        return AICounterAccountResult(
            counter_account_id=account.account_id,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _parse_simple_response(
        self,
        response_text: str,
        account_by_number: dict[str, CounterAccountOption],
    ) -> Optional[AICounterAccountResult]:
        for account_number, account in account_by_number.items():
            if account_number in response_text:
                logger.debug(
                    "Parsed simple response, found account: %s",
                    account_number,
                )
                return AICounterAccountResult(
                    counter_account_id=account.account_id,
                    confidence=0.6,  # Lower confidence for simple parse
                    reasoning="Parsed from unstructured response",
                )

        logger.debug("Could not parse AI response: %s", response_text[:100])
        return None

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check if Ollama is running
                response = await client.get(f"{self._base_url}/api/tags")
                if response.status_code != 200:
                    return False

                # Check if our model is available
                return self._is_model_in_list(response.json())

        except Exception as e:
            logger.debug("Ollama health check failed: %s", str(e))
            return False

    def _is_model_in_list(self, data: dict) -> bool:
        models = [m.get("name", "") for m in data.get("models", [])]

        # Check exact match or partial (qwen2.5:1.5b matches qwen2.5:1.5b)
        model_available = any(
            self._model in model or model.startswith(self._model.split(":")[0])
            for model in models
        )

        if not model_available:
            logger.warning(
                "Model '%s' not found in Ollama. Available: %s",
                self._model,
                models,
            )

        return model_available

    async def is_ollama_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def pull_model(self) -> bool:
        logger.info("Pulling model '%s' from Ollama...", self._model)

        try:
            success = await self._execute_model_pull()
            if success:
                logger.info("Model '%s' pulled successfully!", self._model)
            return success

        except httpx.TimeoutException:
            logger.error(
                "Model pull timed out. The model may still be downloading. "
                "Check: docker logs swen-ollama",
            )
            return False
        except httpx.ConnectError:
            logger.error(
                "Could not connect to Ollama at %s. Is it running?",
                self._base_url,
            )
            return False
        except Exception as e:
            logger.error("Model pull failed: %s", str(e))
            return False

    async def _execute_model_pull(self) -> bool:
        timeout = httpx.Timeout(connect=10.0, read=600.0, write=10.0, pool=10.0)
        url = f"{self._base_url}/api/pull"

        async with (
            httpx.AsyncClient(timeout=timeout) as client,
            client.stream("POST", url, json={"name": self._model}) as response,
        ):
            if response.status_code != 200:
                logger.error(
                    "Failed to pull model '%s': HTTP %s",
                    self._model,
                    response.status_code,
                )
                return False

            return await self._process_pull_stream(response)

    async def _process_pull_stream(self, response: httpx.Response) -> bool:
        last_status = ""

        async for line in response.aiter_lines():
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            if "error" in data:
                logger.error("Model pull failed: %s", data.get("error"))
                return False

            last_status = self._log_pull_progress(data, last_status)

        return True

    def _log_pull_progress(self, data: dict, last_status: str) -> str:
        status = data.get("status", "")

        if not status or status == last_status:
            return last_status

        if "pulling" in status:
            total = data.get("total", 0)
            completed = data.get("completed", 0)
            if total > 0:
                pct = (completed / total) * 100
                logger.info("Downloading %s: %.1f%%", self._model, pct)
        else:
            logger.info("Pull status: %s", status)

        return status

    async def ensure_model_available(self, auto_pull: bool = True) -> bool:
        # First check if model is already available
        if await self.health_check():
            logger.info("Model '%s' is available", self._model)
            return True

        # Check if Ollama is even reachable
        if not await self.is_ollama_reachable():
            logger.warning(
                "Ollama is not reachable at %s. AI features will be disabled.",
                self._base_url,
            )
            return False

        # Model not available - try to pull if auto_pull is enabled
        if auto_pull:
            logger.info(
                "Model '%s' not found. Initiating automatic download...",
                self._model,
            )
            if await self.pull_model():
                return True
            logger.warning(
                "Failed to pull model '%s'. AI features will be disabled.",
                self._model,
            )
            return False
        logger.warning(
            "Model '%s' not available and auto_pull is disabled. Run: ollama pull %s",
            self._model,
            self._model,
        )
        return False
