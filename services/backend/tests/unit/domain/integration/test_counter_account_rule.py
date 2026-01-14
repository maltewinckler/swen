"""Tests for CounterAccountRule value object."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.value_objects import (
    CounterAccountRule,
    PatternType,
    RuleSource,
)

# Test user ID for all tests in this module
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


class TestPatternType:
    """Test cases for PatternType enum."""

    def test_all_pattern_types_exist(self):
        """Test all expected pattern types are defined."""
        assert PatternType.COUNTERPARTY_NAME
        assert PatternType.PURPOSE_TEXT
        assert PatternType.AMOUNT_EXACT
        assert PatternType.AMOUNT_RANGE
        assert PatternType.IBAN
        assert PatternType.COMBINED

    def test_pattern_type_values(self):
        """Test pattern type enum values."""
        assert PatternType.COUNTERPARTY_NAME.value == "counterparty_name"
        assert PatternType.PURPOSE_TEXT.value == "purpose_text"
        assert PatternType.AMOUNT_EXACT.value == "amount_exact"
        assert PatternType.AMOUNT_RANGE.value == "amount_range"
        assert PatternType.IBAN.value == "iban"
        assert PatternType.COMBINED.value == "combined"


class TestRuleSource:
    """Test cases for RuleSource enum."""

    def test_all_rule_sources_exist(self):
        """Test all expected rule sources are defined."""
        assert RuleSource.SYSTEM_DEFAULT
        assert RuleSource.USER_CREATED
        assert RuleSource.AI_LEARNED
        assert RuleSource.AI_GENERATED

    def test_rule_source_values(self):
        """Test rule source enum values."""
        assert RuleSource.SYSTEM_DEFAULT.value == "system_default"
        assert RuleSource.USER_CREATED.value == "user_created"
        assert RuleSource.AI_LEARNED.value == "ai_learned"
        assert RuleSource.AI_GENERATED.value == "ai_generated"


class TestCounterAccountRule:
    """Test cases for CounterAccountRule."""

    def test_counter_account_rule_creation(self):
        """Test creating a basic CounterAccountRule instance."""
        counter_account_id = uuid4()

        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=counter_account_id,
            user_id=TEST_USER_ID,
        )

        assert rule.pattern_type == PatternType.COUNTERPARTY_NAME
        assert rule.pattern_value == "REWE"
        assert rule.counter_account_id == counter_account_id
        assert rule.priority == 100  # Default priority
        assert rule.source == RuleSource.USER_CREATED  # Default source
        assert rule.description is None
        assert rule.is_active is True
        assert rule.match_count == 0
        assert isinstance(rule.id, UUID)
        assert rule.created_at is not None
        assert rule.updated_at is not None
        assert rule.last_matched_at is None

    def test_counter_account_rule_with_all_parameters(self):
        """Test creating CounterAccountRule with all parameters."""
        counter_account_id = uuid4()

        rule = CounterAccountRule(
            pattern_type=PatternType.PURPOSE_TEXT,
            pattern_value="Gehalt",
            counter_account_id=counter_account_id,
            user_id=TEST_USER_ID,
            priority=200,
            source=RuleSource.SYSTEM_DEFAULT,
            description="Salary income",
            is_active=False,
        )

        assert rule.priority == 200
        assert rule.source == RuleSource.SYSTEM_DEFAULT
        assert rule.description == "Salary income"
        assert rule.is_active is False

    def test_counter_account_rule_pattern_value_trimmed(self):
        """Test pattern value is trimmed."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="  REWE  ",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        assert rule.pattern_value == "REWE"

    def test_counter_account_rule_empty_pattern_raises_error(self):
        """Test empty pattern value raises ValueError."""
        with pytest.raises(ValueError, match="Pattern value cannot be empty"):
            CounterAccountRule(
                pattern_type=PatternType.COUNTERPARTY_NAME,
                pattern_value="",
                counter_account_id=uuid4(),
                user_id=TEST_USER_ID,
            )

        with pytest.raises(ValueError, match="Pattern value cannot be empty"):
            CounterAccountRule(
                pattern_type=PatternType.COUNTERPARTY_NAME,
                pattern_value="   ",
                counter_account_id=uuid4(),
                user_id=TEST_USER_ID,
            )

    def test_counter_account_rule_negative_priority_raises_error(self):
        """Test negative priority raises ValueError."""
        with pytest.raises(ValueError, match="Priority must be non-negative"):
            CounterAccountRule(
                pattern_type=PatternType.COUNTERPARTY_NAME,
                pattern_value="REWE",
                counter_account_id=uuid4(),
                user_id=TEST_USER_ID,
                priority=-1,
            )

    def test_matches_counterparty_name(self):
        """Test matching on counterparty name."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        # Create a bank transaction with matching counterparty
        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-50.00"),
            currency="EUR",
            purpose="Groceries",
            applicant_name="REWE Markt GmbH",
        )

        assert rule.matches(tx) is True

    def test_matches_counterparty_name_case_insensitive(self):
        """Test counterparty name matching is case-insensitive."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="rewe",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-50.00"),
            currency="EUR",
            purpose="Groceries",
            applicant_name="REWE MARKT GMBH",
        )

        assert rule.matches(tx) is True

    def test_matches_counterparty_name_partial_match(self):
        """Test counterparty name matching with partial match."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-50.00"),
            currency="EUR",
            purpose="Groceries",
            applicant_name="REWE Center Berlin",
        )

        assert rule.matches(tx) is True

    def test_matches_counterparty_name_no_applicant_name(self):
        """Test counterparty name matching when applicant_name is None."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-50.00"),
            currency="EUR",
            purpose="Groceries",
        )

        assert rule.matches(tx) is False

    def test_matches_purpose_text(self):
        """Test matching on purpose text."""
        rule = CounterAccountRule(
            pattern_type=PatternType.PURPOSE_TEXT,
            pattern_value="Gehalt",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("3000.00"),
            currency="EUR",
            purpose="Gehalt Januar 2025",
        )

        assert rule.matches(tx) is True

    def test_matches_purpose_text_case_insensitive(self):
        """Test purpose text matching is case-insensitive."""
        rule = CounterAccountRule(
            pattern_type=PatternType.PURPOSE_TEXT,
            pattern_value="gehalt",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("3000.00"),
            currency="EUR",
            purpose="GEHALT JANUAR 2025",
        )

        assert rule.matches(tx) is True

    def test_matches_amount_exact(self):
        """Test matching on exact amount."""
        rule = CounterAccountRule(
            pattern_type=PatternType.AMOUNT_EXACT,
            pattern_value="1250.00",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-1250.00"),
            currency="EUR",
            purpose="Rent",
        )

        assert rule.matches(tx) is True

    def test_matches_amount_exact_absolute_value(self):
        """Test amount matching uses absolute value."""
        rule = CounterAccountRule(
            pattern_type=PatternType.AMOUNT_EXACT,
            pattern_value="1250.00",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        # Test with positive amount
        tx_positive = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("1250.00"),
            currency="EUR",
            purpose="Refund",
        )

        assert rule.matches(tx_positive) is True

        # Test with negative amount
        tx_negative = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-1250.00"),
            currency="EUR",
            purpose="Payment",
        )

        assert rule.matches(tx_negative) is True

    def test_matches_amount_exact_invalid_pattern_value(self):
        """Test amount matching with invalid pattern value."""
        rule = CounterAccountRule(
            pattern_type=PatternType.AMOUNT_EXACT,
            pattern_value="not a number",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("100.00"),
            currency="EUR",
            purpose="Test",
        )

        assert rule.matches(tx) is False

    def test_matches_iban(self):
        """Test matching on IBAN."""
        rule = CounterAccountRule(
            pattern_type=PatternType.IBAN,
            pattern_value="DE89370400440532013000",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-100.00"),
            currency="EUR",
            purpose="Transfer",
            applicant_iban="DE89370400440532013000",
        )

        assert rule.matches(tx) is True

    def test_matches_iban_case_insensitive(self):
        """Test IBAN matching is case-insensitive."""
        rule = CounterAccountRule(
            pattern_type=PatternType.IBAN,
            pattern_value="de89370400440532013000",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-100.00"),
            currency="EUR",
            purpose="Transfer",
            applicant_iban="DE89370400440532013000",
        )

        assert rule.matches(tx) is True

    def test_matches_iban_with_spaces(self):
        """Test IBAN matching handles spaces."""
        rule = CounterAccountRule(
            pattern_type=PatternType.IBAN,
            pattern_value="DE89370400440532013000",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-100.00"),
            currency="EUR",
            purpose="Transfer",
            applicant_iban="DE89 3704 0044 0532 0130 00",
        )

        assert rule.matches(tx) is True

    def test_matches_iban_no_applicant_iban(self):
        """Test IBAN matching when applicant_iban is None."""
        rule = CounterAccountRule(
            pattern_type=PatternType.IBAN,
            pattern_value="DE89370400440532013000",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-100.00"),
            currency="EUR",
            purpose="Transfer",
        )

        assert rule.matches(tx) is False

    def test_matches_inactive_rule_returns_false(self):
        """Test inactive rules never match."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
            is_active=False,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("-50.00"),
            currency="EUR",
            purpose="Groceries",
            applicant_name="REWE Markt GmbH",
        )

        assert rule.matches(tx) is False

    def test_matches_unimplemented_pattern_type_returns_false(self):
        """Test unimplemented pattern types return False."""
        rule = CounterAccountRule(
            pattern_type=PatternType.AMOUNT_RANGE,
            pattern_value="100-200",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        tx = BankTransaction(
            booking_date=date(2025, 1, 1),
            value_date=date(2025, 1, 1),
            amount=Decimal("150.00"),
            currency="EUR",
            purpose="Test",
        )

        assert rule.matches(tx) is False

    def test_record_match(self):
        """Test recording a match updates count and timestamp."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        assert rule.match_count == 0
        assert rule.last_matched_at is None
        original_updated_at = rule.updated_at

        rule.record_match()

        assert rule.match_count == 1
        assert rule.last_matched_at is not None
        assert rule.updated_at > original_updated_at

    def test_record_multiple_matches(self):
        """Test recording multiple matches increments count."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        rule.record_match()
        rule.record_match()
        rule.record_match()

        assert rule.match_count == 3

    def test_update_priority(self):
        """Test updating rule priority."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
            priority=100,
        )

        original_updated_at = rule.updated_at

        rule.update_priority(200)

        assert rule.priority == 200
        assert rule.updated_at > original_updated_at

    def test_update_priority_negative_raises_error(self):
        """Test updating priority to negative value raises ValueError."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        with pytest.raises(ValueError, match="Priority must be non-negative"):
            rule.update_priority(-1)

    def test_deactivate_rule(self):
        """Test deactivating a rule."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        assert rule.is_active is True
        original_updated_at = rule.updated_at

        rule.deactivate()

        assert rule.is_active is False
        assert rule.updated_at > original_updated_at

    def test_activate_rule(self):
        """Test activating a rule."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
            is_active=False,
        )

        assert rule.is_active is False
        original_updated_at = rule.updated_at

        rule.activate()

        assert rule.is_active is True
        assert rule.updated_at > original_updated_at

    def test_update_counter_account(self):
        """Test updating the counter-account."""
        old_counter_account_id = uuid4()
        new_counter_account_id = uuid4()

        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=old_counter_account_id,
            user_id=TEST_USER_ID,
        )

        original_updated_at = rule.updated_at

        rule.update_counter_account(new_counter_account_id)

        assert rule.counter_account_id == new_counter_account_id
        assert rule.updated_at > original_updated_at

    def test_equality(self):
        """Test equality comparison based on ID."""
        rule1 = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        rule2 = rule1  # Same instance

        assert rule1 == rule2

    def test_inequality(self):
        """Test inequality comparison."""
        rule1 = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        rule2 = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="EDEKA",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        assert rule1 != rule2

    def test_equality_with_non_counter_account_rule(self):
        """Test equality comparison with non-CounterAccountRule object."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        assert rule != "not a rule"
        assert rule != 123
        assert rule is not None

    def test_hashable(self):
        """Test CounterAccountRule can be used in sets and as dict keys."""
        rule1 = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        rule2 = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="EDEKA",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        # Can be added to set
        rule_set = {rule1, rule2}
        assert len(rule_set) == 2

        # Can be used as dict key
        rule_dict = {rule1: "groceries1", rule2: "groceries2"}
        assert rule_dict[rule1] == "groceries1"

    def test_string_representation(self):
        """Test string representation of CounterAccountRule."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
            priority=150,
        )

        str_repr = str(rule)

        assert "CounterAccountRule" in str_repr
        assert "ACTIVE" in str_repr
        assert "counterparty_name" in str_repr
        assert "REWE" in str_repr
        assert "priority=150" in str_repr
        assert "matches=0" in str_repr

    def test_string_representation_inactive(self):
        """Test string representation of inactive rule."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
            is_active=False,
        )

        str_repr = str(rule)

        assert "INACTIVE" in str_repr

    def test_string_representation_with_matches(self):
        """Test string representation includes match count."""
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=uuid4(),
            user_id=TEST_USER_ID,
        )

        rule.record_match()
        rule.record_match()

        str_repr = str(rule)

        assert "matches=2" in str_repr

    def test_multiple_rules_with_different_priorities(self):
        """Test creating multiple rules with different priorities."""
        counter_account_id = uuid4()

        high_priority = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="Specific Merchant",
            counter_account_id=counter_account_id,
            user_id=TEST_USER_ID,
            priority=200,
        )

        low_priority = CounterAccountRule(
            pattern_type=PatternType.PURPOSE_TEXT,
            pattern_value="General",
            counter_account_id=counter_account_id,
            user_id=TEST_USER_ID,
            priority=50,
        )

        assert high_priority.priority > low_priority.priority

