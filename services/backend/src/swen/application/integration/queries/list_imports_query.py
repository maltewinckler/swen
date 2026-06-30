"""List imports query - retrieve transaction imports for display."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from swen.application.integration.dtos import (
    ImportedTransactionDTO,
    ImportedTransactionsListDTO,
)
from swen.domain.integration.value_objects import ImportStatus
from swen.domain.shared.time import ensure_tz_aware, utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.integration.entities import TransactionImport
    from swen.domain.integration.repositories import TransactionImportRepository


class ListImportsQuery:
    """Query to list transaction imports with filters."""

    def __init__(self, import_repository: TransactionImportRepository):
        self._import_repo = import_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ListImportsQuery:
        return cls(import_repository=factory.import_repository())

    async def execute(
        self,
        days: int = 30,
        limit: int = 50,
        failed_only: bool = False,
        iban_filter: str | None = None,  # noqa: ARG002 - future relevance?
    ) -> ImportedTransactionsListDTO:
        """List transaction imports with status counts.

        Returns
        -------
            ImportedTransactionsListDTO containing import records with
            their status counts.
        """
        end_date = utc_now()
        start_date = end_date - timedelta(days=days)

        if failed_only:
            imports = await self._import_repo.find_failed_imports()
        else:
            all_imports: list[TransactionImport] = []
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

        dtos = [
            ImportedTransactionDTO(
                id=imp.id,
                bank_transaction_id=imp.bank_transaction_id,
                status=imp.status.value,
                error_message=imp.error_message,
                transaction_id=imp.accounting_transaction_id,
                created_at=imp.created_at,
                imported_at=imp.imported_at,
            )
            for imp in imports
        ]

        return ImportedTransactionsListDTO(
            imports=dtos,
            count=len(dtos),
            status_counts=status_counts,
        )
