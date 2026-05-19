"""List imports query - retrieve transaction imports for display."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from swen.domain.integration.entities import TransactionImport
from swen.domain.integration.repositories import TransactionImportRepository
from swen.domain.integration.value_objects import ImportStatus
from swen.domain.shared.time import ensure_tz_aware, utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass
class ImportListResult:
    """Result of listing imports."""

    imports: list[TransactionImport]
    total_count: int
    status_counts: dict[str, int]


class ListImportsQuery:
    """Query to list transaction imports with filters."""

    def __init__(
        self,
        import_repository: TransactionImportRepository,
    ):
        self._import_repo = import_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ListImportsQuery:
        return cls(import_repository=factory.import_repository())

    async def execute(
        self,
        days: int = 30,
        limit: int = 50,
        failed_only: bool = False,
        iban_filter: Optional[str] = None,  # noqa: ARG002 - future relevance?
    ) -> ImportListResult:
        end_date = utc_now()
        start_date = end_date - timedelta(days=days)

        if failed_only:
            imports = await self._import_repo.find_failed_imports()
        else:
            all_imports = []
            for status in ImportStatus:
                status_imports = await self._import_repo.find_by_status(status)
                all_imports.extend(status_imports)

            imports = [
                imp
                for imp in all_imports
                if ensure_tz_aware(imp.created_at) >= start_date
                and ensure_tz_aware(imp.created_at) <= end_date
            ]

        imports = sorted(imports, key=lambda x: x.created_at, reverse=True)[:limit]

        status_counts: dict[str, int] = {}
        for imp in imports:
            status_val = imp.status.value
            status_counts[status_val] = status_counts.get(status_val, 0) + 1

        return ImportListResult(
            imports=imports,
            total_count=len(imports),
            status_counts=status_counts,
        )

    async def has_recent_failures(
        self,
        iban: str,
        since: datetime,
    ) -> bool:
        iban_imports = await self._import_repo.find_by_iban(iban)
        recent_failures = [
            imp
            for imp in iban_imports
            if imp.is_failed() and ensure_tz_aware(imp.created_at) >= since
        ]
        return len(recent_failures) > 0
