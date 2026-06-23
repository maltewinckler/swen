"""Sync status query. Retrieve sync statistics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from swen.domain.integration.repositories import TransactionImportRepository
from swen.domain.integration.value_objects import ImportStatus

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass
class SyncStatusResult:
    """Result of sync status query."""

    success_count: int
    failed_count: int
    pending_count: int
    duplicate_count: int
    skipped_count: int
    total_count: int


class SyncStatusQuery:
    """Query to get sync status statistics."""

    def __init__(self, import_repository: TransactionImportRepository):
        self._import_repo = import_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> SyncStatusQuery:
        return cls(import_repository=factory.import_repository())

    async def execute(self) -> SyncStatusResult:
        total = await self._import_repo.count_by_status()

        success = total.get(ImportStatus.SUCCESS.value, 0)
        failed = total.get(ImportStatus.FAILED.value, 0)
        pending = total.get(ImportStatus.PENDING.value, 0)
        duplicate = total.get(ImportStatus.DUPLICATE.value, 0)
        skipped = total.get(ImportStatus.SKIPPED.value, 0)

        return SyncStatusResult(
            success_count=success,
            failed_count=failed,
            pending_count=pending,
            duplicate_count=duplicate,
            skipped_count=skipped,
            total_count=sum(total.values()),
        )
