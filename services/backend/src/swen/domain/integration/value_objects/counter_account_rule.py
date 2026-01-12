"""Counter-account rule value object."""

from datetime import datetime

from swen.domain.shared.time import utc_now
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from swen.domain.banking.value_objects import BankTransaction


class PatternType(Enum):
    """Type of pattern matching for counter-account rules."""

    COUNTERPARTY_NAME = "counterparty_name"
    PURPOSE_TEXT = "purpose_text"
    AMOUNT_EXACT = "amount_exact"
    AMOUNT_RANGE = "amount_range"
    IBAN = "iban"
    COMBINED = "combined"


class RuleSource(Enum):
    """Source/origin of the counter-account rule."""

    SYSTEM_DEFAULT = "system_default"
    USER_CREATED = "user_created"
    AI_LEARNED = "ai_learned"
    AI_GENERATED = "ai_generated"


class CounterAccountRule:
    """Rule for automatically resolving the Counter-Account for bank transactions."""

    def __init__(  # NOQA: PLR0913
        self,
        pattern_type: PatternType,
        pattern_value: str,
        counter_account_id: UUID,
        user_id: UUID,
        priority: int = 100,
        source: RuleSource = RuleSource.USER_CREATED,
        description: Optional[str] = None,
        is_active: bool = True,
    ):
        self._id = uuid4()
        self._user_id = user_id
        self._pattern_type = pattern_type
        self._pattern_value = pattern_value.strip()
        self._counter_account_id = counter_account_id
        self._priority = priority
        self._source = source
        self._description = description
        self._is_active = is_active
        self._match_count = 0
        self._created_at = utc_now()
        self._updated_at = utc_now()
        self._last_matched_at: Optional[datetime] = None

        self._validate()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def pattern_type(self) -> PatternType:
        return self._pattern_type

    @property
    def pattern_value(self) -> str:
        return self._pattern_value

    @property
    def counter_account_id(self) -> UUID:
        return self._counter_account_id

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def source(self) -> RuleSource:
        return self._source

    @property
    def description(self) -> Optional[str]:
        return self._description

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def match_count(self) -> int:
        return self._match_count

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def last_matched_at(self) -> Optional[datetime]:
        return self._last_matched_at

    def _validate(self) -> None:
        if not self._pattern_value:
            msg = "Pattern value cannot be empty"
            raise ValueError(msg)

        if self._priority < 0:
            msg = "Priority must be non-negative"
            raise ValueError(msg)

    def matches(self, bank_transaction: BankTransaction) -> bool:  # NOQA: PLR0911
        if not self._is_active:
            return False

        # Case-insensitive matching
        pattern_lower = self._pattern_value.lower()

        if self._pattern_type == PatternType.COUNTERPARTY_NAME:
            if bank_transaction.applicant_name:
                return pattern_lower in bank_transaction.applicant_name.lower()
            return False

        if self._pattern_type == PatternType.PURPOSE_TEXT:
            return pattern_lower in bank_transaction.purpose.lower()

        if self._pattern_type == PatternType.AMOUNT_EXACT:
            # Convert pattern to decimal for comparison
            try:
                pattern_amount = abs(Decimal(self._pattern_value))
                transaction_amount = abs(bank_transaction.amount)
                return pattern_amount == transaction_amount
            except (ValueError, TypeError, Exception):
                return False

        elif self._pattern_type == PatternType.IBAN:
            if bank_transaction.applicant_iban:
                return pattern_lower == bank_transaction.applicant_iban.lower().replace(
                    " ",
                    "",
                )
            return False

        # Other pattern types not yet implemented
        return False

    def record_match(self) -> None:
        self._match_count += 1
        self._last_matched_at = utc_now()
        self._updated_at = utc_now()

    def update_priority(self, new_priority: int) -> None:
        if new_priority < 0:
            msg = "Priority must be non-negative"
            raise ValueError(msg)

        self._priority = new_priority
        self._updated_at = utc_now()

    def deactivate(self) -> None:
        self._is_active = False
        self._updated_at = utc_now()

    def activate(self) -> None:
        self._is_active = True
        self._updated_at = utc_now()

    def update_counter_account(self, new_counter_account_id: UUID) -> None:
        self._counter_account_id = new_counter_account_id
        self._updated_at = utc_now()

    def __eq__(self, other) -> bool:
        if not isinstance(other, CounterAccountRule):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __str__(self) -> str:
        status = "ACTIVE" if self._is_active else "INACTIVE"
        return (
            f"CounterAccountRule[{status}]: "
            f"{self._pattern_type.value}='{self._pattern_value}' "
            f"(priority={self._priority}, matches={self._match_count})"
        )
