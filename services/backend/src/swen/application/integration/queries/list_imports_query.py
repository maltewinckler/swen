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


@dataclass
class ImportStatistics:
    """Import statistics with timestamps."""

    iban: Optional[str]  # None for global statistics
    total_imports: int
    successful_imports: int
    failed_imports: int
    pending_imports: int
    duplicate_imports: int
    skipped_imports: int
    last_import_at: Optional[datetime]
    oldest_import_at: Optional[datetime]


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

    async def get_status_statistics(self) -> dict[str, int]:
        return await self._import_repo.count_by_status()

    async def get_statistics(
        self,
        iban: Optional[str] = None,
    ) -> ImportStatistics:
        status_counts = await self._import_repo.count_by_status(iban)

        if iban:
            all_imports = await self._import_repo.find_by_iban(iban)
        else:
            all_imports = []
            for status in ImportStatus:
                status_imports = await self._import_repo.find_by_status(status)
                all_imports.extend(status_imports)

        last_import_at = None
        oldest_import_at = None

        if all_imports:
            valid_imports = [imp for imp in all_imports if imp.imported_at]
            if valid_imports:
                sorted_imports = sorted(
                    valid_imports,
                    key=lambda imp: imp.imported_at,  # type: ignore[arg-type, return-value]
                )
                oldest_import_at = sorted_imports[0].imported_at
                last_import_at = sorted_imports[-1].imported_at

        return ImportStatistics(
            iban=iban,
            total_imports=sum(status_counts.values()),
            successful_imports=status_counts.get(ImportStatus.SUCCESS.value, 0),
            failed_imports=status_counts.get(ImportStatus.FAILED.value, 0),
            pending_imports=status_counts.get(ImportStatus.PENDING.value, 0),
            duplicate_imports=status_counts.get(ImportStatus.DUPLICATE.value, 0),
            skipped_imports=status_counts.get(ImportStatus.SKIPPED.value, 0),
            last_import_at=last_import_at,
            oldest_import_at=oldest_import_at,
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
