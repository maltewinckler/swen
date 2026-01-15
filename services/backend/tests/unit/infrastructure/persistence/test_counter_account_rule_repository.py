"""
Unit tests for CounterAccountRuleRepositorySQLAlchemy.

Tests the persistence of counter-account rules for automatic transaction counter-account resolution.
"""

from uuid import uuid4

import pytest
from sqlalchemy import select

from swen.domain.integration.value_objects import (
    CounterAccountRule,
    PatternType,
    RuleSource,
)
from swen.infrastructure.persistence.sqlalchemy.models.integration import (
    CounterAccountRuleModel,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    CounterAccountRuleRepositorySQLAlchemy,
)
from tests.unit.infrastructure.persistence.conftest import TEST_USER_ID


# Helper function to create test rule
def create_test_rule(**overrides) -> CounterAccountRule:
    """Create a test counter-account rule with default values."""
    defaults = {
        "pattern_type": PatternType.COUNTERPARTY_NAME,
        "pattern_value": "REWE",
        "counter_account_id": uuid4(),
        "priority": 100,
        "source": RuleSource.USER_CREATED,
        "description": "Test rule",
        "is_active": True,
        "user_id": TEST_USER_ID,
    }
    defaults.update(overrides)
    return CounterAccountRule(**defaults)


@pytest.mark.asyncio
class TestCounterAccountRuleRepositorySQLAlchemy:
    """Test suite for CounterAccountRuleRepositorySQLAlchemy."""

    async def test_save_new_rule(self, async_session, current_user):
        """Test saving a new counter-account rule."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)
        rule = create_test_rule()

        # Act
        await repo.save(rule)
        await async_session.commit()

        # Assert - verify it was saved in database
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.id == rule.id,
        )
        result = await async_session.execute(stmt)
        saved_model = result.scalar_one_or_none()

        assert saved_model is not None
        assert saved_model.id == rule.id
        assert saved_model.pattern_type == rule.pattern_type
        assert saved_model.pattern_value == rule.pattern_value
        assert saved_model.counter_account_id == rule.counter_account_id
        assert saved_model.priority == rule.priority

    async def test_save_updates_existing_rule(self, async_session, current_user):
        """Test that saving an existing rule updates it."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)
        rule = create_test_rule()
        await repo.save(rule)
        await async_session.commit()

        # Act - update the rule
        rule.update_priority(200)
        await repo.save(rule)
        await async_session.commit()

        # Assert
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.id == rule.id,
        )
        result = await async_session.execute(stmt)
        updated_model = result.scalar_one_or_none()

        assert updated_model is not None
        assert updated_model.priority == 200

    async def test_find_by_id(self, async_session, current_user):
        """Test finding a rule by ID."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)
        rule = create_test_rule()
        await repo.save(rule)
        await async_session.commit()

        # Act
        found_rule = await repo.find_by_id(rule.id)

        # Assert
        assert found_rule is not None
        assert found_rule.id == rule.id
        assert found_rule.pattern_value == rule.pattern_value

    async def test_find_by_id_returns_none_when_not_found(
        self, async_session, current_user
    ):
        """Test that find_by_id returns None for non-existent rule."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)
        non_existent_id = uuid4()

        # Act
        found_rule = await repo.find_by_id(non_existent_id)

        # Assert
        assert found_rule is None

    async def test_find_all_active_ordered_by_priority(
        self, async_session, current_user
    ):
        """Test finding all active rules ordered by priority."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)

        rule1 = create_test_rule(
            pattern_value="Low Priority",
            priority=50,
            is_active=True,
        )
        rule2 = create_test_rule(
            pattern_value="High Priority",
            priority=200,
            is_active=True,
        )
        rule3 = create_test_rule(
            pattern_value="Inactive",
            priority=300,
            is_active=False,
        )

        await repo.save(rule1)
        await repo.save(rule2)
        await repo.save(rule3)
        await async_session.commit()

        # Act
        active_rules = await repo.find_all_active()

        # Assert
        assert len(active_rules) == 2
        # Should be ordered by priority descending
        assert active_rules[0].priority == 200
        assert active_rules[1].priority == 50
        assert all(r.is_active for r in active_rules)

    async def test_find_all(self, async_session, current_user):
        """Test finding all rules (active and inactive)."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)

        rule1 = create_test_rule(pattern_value="Active", is_active=True)
        rule2 = create_test_rule(pattern_value="Inactive", is_active=False)

        await repo.save(rule1)
        await repo.save(rule2)
        await async_session.commit()

        # Act
        all_rules = await repo.find_all()

        # Assert
        assert len(all_rules) == 2

    async def test_find_by_pattern_type(self, async_session, current_user):
        """Test finding rules by pattern type."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)

        rule1 = create_test_rule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
        )
        rule2 = create_test_rule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="EDEKA",
        )
        rule3 = create_test_rule(
            pattern_type=PatternType.PURPOSE_TEXT,
            pattern_value="Gehalt",
        )

        await repo.save(rule1)
        await repo.save(rule2)
        await repo.save(rule3)
        await async_session.commit()

        # Act
        counterparty_rules = await repo.find_by_pattern_type(
            PatternType.COUNTERPARTY_NAME,
        )

        # Assert
        assert len(counterparty_rules) == 2
        assert all(
            r.pattern_type == PatternType.COUNTERPARTY_NAME for r in counterparty_rules
        )

    async def test_find_by_source(self, async_session, current_user):
        """Test finding rules by source."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)

        rule1 = create_test_rule(
            pattern_value="User Rule 1",
            source=RuleSource.USER_CREATED,
        )
        rule2 = create_test_rule(
            pattern_value="User Rule 2",
            source=RuleSource.USER_CREATED,
        )
        rule3 = create_test_rule(
            pattern_value="System Rule",
            source=RuleSource.SYSTEM_DEFAULT,
        )

        await repo.save(rule1)
        await repo.save(rule2)
        await repo.save(rule3)
        await async_session.commit()

        # Act
        user_rules = await repo.find_by_source(RuleSource.USER_CREATED)

        # Assert
        assert len(user_rules) == 2
        assert all(r.source == RuleSource.USER_CREATED for r in user_rules)

    async def test_find_by_counter_account(self, async_session, current_user):
        """Test finding rules by counter-account."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)
        counter_account_id = uuid4()

        rule1 = create_test_rule(
            pattern_value="Rule 1",
            counter_account_id=counter_account_id,
        )
        rule2 = create_test_rule(
            pattern_value="Rule 2",
            counter_account_id=counter_account_id,
        )
        rule3 = create_test_rule(
            pattern_value="Other",
            counter_account_id=uuid4(),
        )

        await repo.save(rule1)
        await repo.save(rule2)
        await repo.save(rule3)
        await async_session.commit()

        # Act
        counter_account_rules = await repo.find_by_counter_account(counter_account_id)

        # Assert
        assert len(counter_account_rules) == 2
        assert all(
            r.counter_account_id == counter_account_id for r in counter_account_rules
        )

    async def test_delete_rule(self, async_session, current_user):
        """Test deleting a rule."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)
        rule = create_test_rule()
        await repo.save(rule)
        await async_session.commit()

        # Act
        deleted = await repo.delete(rule.id)
        await async_session.commit()

        # Assert
        assert deleted is True

        # Verify it's gone from database
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.id == rule.id,
        )
        result = await async_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_delete_nonexistent_rule_returns_false(
        self, async_session, current_user
    ):
        """Test that deleting a non-existent rule returns False."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)
        non_existent_id = uuid4()

        # Act
        deleted = await repo.delete(non_existent_id)

        # Assert
        assert deleted is False

    async def test_count_by_source(self, async_session, current_user):
        """Test counting rules by source."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)

        rule1 = create_test_rule(
            pattern_value="User 1",
            source=RuleSource.USER_CREATED,
        )
        rule2 = create_test_rule(
            pattern_value="User 2",
            source=RuleSource.USER_CREATED,
        )
        rule3 = create_test_rule(
            pattern_value="System",
            source=RuleSource.SYSTEM_DEFAULT,
        )

        await repo.save(rule1)
        await repo.save(rule2)
        await repo.save(rule3)
        await async_session.commit()

        # Act
        counts = await repo.count_by_source()

        # Assert
        assert counts.get("user_created", 0) == 2
        assert counts.get("system_default", 0) == 1

    async def test_domain_to_model_mapping_preserves_all_fields(
        self, async_session, current_user
    ):
        """Test that all domain fields are correctly mapped to model and back."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)
        rule = create_test_rule(
            pattern_type=PatternType.PURPOSE_TEXT,
            pattern_value="Specific Pattern",
            priority=150,
            source=RuleSource.AI_LEARNED,
            description="Test description",
            is_active=False,
        )

        # Act - save and retrieve
        await repo.save(rule)
        await async_session.commit()
        retrieved_rule = await repo.find_by_id(rule.id)

        # Assert - all fields preserved
        assert retrieved_rule is not None
        assert retrieved_rule.id == rule.id
        assert retrieved_rule.pattern_type == rule.pattern_type
        assert retrieved_rule.pattern_value == rule.pattern_value
        assert retrieved_rule.counter_account_id == rule.counter_account_id
        assert retrieved_rule.priority == rule.priority
        assert retrieved_rule.source == rule.source
        assert retrieved_rule.description == rule.description
        assert retrieved_rule.is_active == rule.is_active
        assert retrieved_rule.match_count == rule.match_count
        assert retrieved_rule.created_at.replace(
            tzinfo=None,
        ) == rule.created_at.replace(tzinfo=None)

    async def test_record_match_updates_statistics(self, async_session, current_user):
        """Test that recording a match updates statistics."""
        # Arrange
        repo = CounterAccountRuleRepositorySQLAlchemy(async_session, current_user)
        rule = create_test_rule()
        await repo.save(rule)
        await async_session.commit()

        # Act - record match
        rule.record_match()
        await repo.save(rule)
        await async_session.commit()

        # Assert
        retrieved = await repo.find_by_id(rule.id)
        assert retrieved is not None
        assert retrieved.match_count == 1
        assert retrieved.last_matched_at is not None
