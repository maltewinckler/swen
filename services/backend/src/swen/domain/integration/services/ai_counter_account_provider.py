"""AI Counter-Account Provider interface."""

from abc import ABC, abstractmethod
from typing import Optional

from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.value_objects import (
    AICounterAccountResult,
    CounterAccountOption,
)


class AICounterAccountProvider(ABC):
    """Abstract interface for AI-powered counter-account resolution."""

    @abstractmethod
    async def resolve(
        self,
        transaction: BankTransaction,
        available_accounts: list[CounterAccountOption],
    ) -> Optional[AICounterAccountResult]:
        """
        Resolve the Counter-Account for a bank transaction using AI.

        Implementations should handle errors gracefully and return None
        if the AI service is unavailable or returns an invalid response.

        Parameters
        ----------
        transaction
            The bank transaction to classify
        available_accounts
            List of accounts the AI can choose from

        Returns
        -------
        AICounterAccountResult if AI can make a suggestion, None otherwise.
        Result includes the suggested account ID, confidence score,
        and optional reasoning.
        """

    @property
    @abstractmethod
    def min_confidence_threshold(self) -> float:
        """
        Minimum confidence threshold for this provider.

        Results with confidence below this threshold should typically be
        treated as uncertain and may fall back to default account.

        Returns
        -------
        Float between 0.0 and 1.0 (typically 0.6-0.8)
        """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Name/identifier of the AI model being used.

        Used for logging, debugging, and storing in transaction metadata
        to track which model made each prediction.

        Returns
        -------
        Model identifier string (e.g., "qwen2.5:1.5b", "gpt-4o-mini")
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the AI provider is healthy and available.

        Returns
        -------
        True if the provider is ready to process requests, False otherwise.
        """

    @abstractmethod
    async def ensure_model_available(self, auto_pull: bool = True) -> bool:
        """
        Ensure the AI model is available, optionally downloading it.

        Parameters
        ----------
        auto_pull
            If True, attempt to download the model if not available.

        Returns
        -------
        True if the model is available and ready, False otherwise.
        """
