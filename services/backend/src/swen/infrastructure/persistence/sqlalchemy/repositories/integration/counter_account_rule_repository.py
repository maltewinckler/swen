"""SQLAlchemy implementation of CounterAccountRuleRepository."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from swen.domain.integration.repositories import CounterAccountRuleRepository
from swen.domain.integration.value_objects import (
    CounterAccountRule,
    PatternType,
    RuleSource,
)
from swen.infrastructure.persistence.sqlalchemy.models.integration import (
    CounterAccountRuleModel,
)

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser


class CounterAccountRuleRepositorySQLAlchemy(CounterAccountRuleRepository):
    """SQLAlchemy implementation of CounterAccountRuleRepository."""

    def __init__(self, session: AsyncSession, current_user: CurrentUser):
        self._session = session
        self._user_id = current_user.user_id

    async def save(self, rule: CounterAccountRule) -> None:
        # Check if rule exists
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.id == rule.id,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing rule
            existing.user_id = rule.user_id
            existing.pattern_type = rule.pattern_type
            existing.pattern_value = rule.pattern_value
            existing.counter_account_id = rule.counter_account_id
            existing.priority = rule.priority
            existing.source = rule.source
            existing.description = rule.description
            existing.is_active = rule.is_active
            existing.match_count = rule.match_count
            existing.last_matched_at = rule.last_matched_at
            existing.updated_at = rule.updated_at
        else:
            # Create new rule
            model = CounterAccountRuleModel(
                id=rule.id,
                user_id=rule.user_id,
                pattern_type=rule.pattern_type,
                pattern_value=rule.pattern_value,
                counter_account_id=rule.counter_account_id,
                priority=rule.priority,
                source=rule.source,
                description=rule.description,
                is_active=rule.is_active,
                match_count=rule.match_count,
                last_matched_at=rule.last_matched_at,
                created_at=rule.created_at,
                updated_at=rule.updated_at,
            )
            self._session.add(model)

        await self._session.flush()

    async def find_by_id(self, rule_id: UUID) -> Optional[CounterAccountRule]:
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.user_id == self._user_id,
            CounterAccountRuleModel.id == rule_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_domain(model)

    async def find_all_active(self) -> List[CounterAccountRule]:
        stmt = (
            select(CounterAccountRuleModel)
            .where(
                CounterAccountRuleModel.user_id == self._user_id,
                CounterAccountRuleModel.is_active == True,  # NOQA: E712
            )
            .order_by(CounterAccountRuleModel.priority.desc())
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_all(self) -> List[CounterAccountRule]:
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.user_id == self._user_id,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_by_pattern_type(
        self,
        pattern_type: PatternType,
    ) -> List[CounterAccountRule]:
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.user_id == self._user_id,
            CounterAccountRuleModel.pattern_type == pattern_type,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_by_source(self, source: RuleSource) -> List[CounterAccountRule]:
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.user_id == self._user_id,
            CounterAccountRuleModel.source == source,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def find_by_counter_account(
        self,
        counter_account_id: UUID,
    ) -> List[CounterAccountRule]:
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.user_id == self._user_id,
            CounterAccountRuleModel.counter_account_id == counter_account_id,
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._model_to_domain(model) for model in models]

    async def delete(self, rule_id: UUID) -> bool:
        stmt = select(CounterAccountRuleModel).where(
            CounterAccountRuleModel.user_id == self._user_id,
            CounterAccountRuleModel.id == rule_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        await self._session.delete(model)
        await self._session.flush()
        return True

    async def count_by_source(self) -> dict[str, int]:
        stmt = (
            select(
                CounterAccountRuleModel.source,
                func.count(CounterAccountRuleModel.id),
            )
            .where(CounterAccountRuleModel.user_id == self._user_id)
            .group_by(CounterAccountRuleModel.source)
        )

        result = await self._session.execute(stmt)
        rows = result.all()

        return {source.value: count for source, count in rows}

    def _model_to_domain(self, model: CounterAccountRuleModel) -> CounterAccountRule:
        rule = CounterAccountRule.__new__(CounterAccountRule)
        rule._id = model.id
        rule._user_id = model.user_id
        rule._pattern_type = model.pattern_type
        rule._pattern_value = model.pattern_value
        rule._counter_account_id = model.counter_account_id
        rule._priority = model.priority
        rule._source = model.source
        rule._description = model.description
        rule._is_active = model.is_active
        rule._match_count = model.match_count
        rule._last_matched_at = model.last_matched_at
        rule._created_at = model.created_at
        rule._updated_at = model.updated_at

        return rule
