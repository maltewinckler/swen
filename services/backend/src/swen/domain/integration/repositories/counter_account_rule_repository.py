"""Repository interface for counter-account rules.

THIS IS NOT USED YET.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from swen.domain.integration.value_objects import (
    CounterAccountRule,
    PatternType,
    RuleSource,
)


class CounterAccountRuleRepository(ABC):
    """Repository interface for persisting and retrieving counter-account rules."""

    @abstractmethod
    async def save(self, rule: CounterAccountRule) -> None:
        """
        Save a counter-account rule.

        Parameters
        ----------
        rule
            Counter-account rule to save
        """

    @abstractmethod
    async def find_by_id(self, rule_id: UUID) -> Optional[CounterAccountRule]:
        """
        Find a counter-account rule by ID.

        Parameters
        ----------
        rule_id
            Rule ID to search for

        Returns
        -------
        Counter-account rule if found, None otherwise
        """

    @abstractmethod
    async def find_all_active(self) -> List[CounterAccountRule]:
        """
        Find all active counter-account rules, ordered by priority (descending).

        Returns
        -------
        List of active rules sorted by priority (may be empty)
        """

    @abstractmethod
    async def find_all(self) -> List[CounterAccountRule]:
        """
        Find all counter-account rules (active and inactive).

        Returns
        -------
        List of all rules (may be empty)
        """

    @abstractmethod
    async def find_by_pattern_type(
        self,
        pattern_type: PatternType,
    ) -> List[CounterAccountRule]:
        """
        Find all rules with a specific pattern type.

        Parameters
        ----------
        pattern_type
            Pattern type to filter by

        Returns
        -------
        List of matching rules (may be empty)
        """

    @abstractmethod
    async def find_by_source(self, source: RuleSource) -> List[CounterAccountRule]:
        """
        Find all rules from a specific source.

        Parameters
        ----------
        source
            Rule source to filter by

        Returns
        -------
        List of matching rules (may be empty)
        """

    @abstractmethod
    async def find_by_counter_account(
        self,
        counter_account_id: UUID,
    ) -> List[CounterAccountRule]:
        """
        Find all rules that target a specific counter-account.

        Parameters
        ----------
        counter_account_id
            Counter-account ID

        Returns
        -------
        List of rules targeting this counter-account (may be empty)
        """

    @abstractmethod
    async def delete(self, rule_id: UUID) -> bool:
        """
        Delete a counter-account rule.

        Parameters
        ----------
        rule_id
            Rule ID to delete

        Returns
        -------
        True if deleted, False if not found
        """

    @abstractmethod
    async def count_by_source(self) -> dict[str, int]:
        """
        Count rules by source type.

        Returns
        -------
        Dictionary mapping source name to count
        Example
            {"user_created": 25, "system_default": 10, "ai_learned": 5}
        """
