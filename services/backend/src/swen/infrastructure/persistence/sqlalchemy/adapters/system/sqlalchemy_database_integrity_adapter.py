"""SQLAlchemy implementation of DatabaseIntegrityPort.

This adapter implements the database integrity operations using SQLAlchemy,
keeping the application layer free from database-specific dependencies.

Note: These operations are not user-scoped - they operate on the entire
database for system-level integrity maintenance.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from swen.application.ports.system import DatabaseIntegrityPort


class SqlAlchemyDatabaseIntegrityAdapter(DatabaseIntegrityPort):
    """SQLAlchemy implementation of database integrity operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def find_orphan_transaction_ids(
        self,
        *,
        opening_balance_metadata_key: str,
        source_metadata_key: str,
    ) -> tuple[str, ...]:
        query = text("""
            SELECT t.id
            FROM accounting_transactions t
            LEFT JOIN transaction_imports ti ON t.id = ti.accounting_transaction_id
            WHERE ti.id IS NULL
              AND t.transaction_metadata NOT LIKE :opening_balance_pattern
              AND t.transaction_metadata NOT LIKE :source_opening_pattern
              AND t.transaction_metadata NOT LIKE :source_manual_pattern
            ORDER BY t.date
        """)
        params = {
            "opening_balance_pattern": f'%"{opening_balance_metadata_key}": true%',
            "source_opening_pattern": f'%"{source_metadata_key}": "opening_balance"%',
            "source_manual_pattern": f'%"{source_metadata_key}": "manual"%',
        }
        result = await self._session.execute(query, params)
        rows = result.fetchall()
        return tuple(str(row[0]) for row in rows)

    async def find_duplicate_transaction_ids(self) -> tuple[str, ...]:
        query = text("""
            SELECT t.date, t.description, je.debit_amount, je.credit_amount,
                   COUNT(*) as count,
                   GROUP_CONCAT(t.id) as transaction_ids
            FROM journal_entries je
            JOIN accounting_transactions t ON je.transaction_id = t.id
            JOIN accounting_accounts a ON je.account_id = a.id
            WHERE a.account_type = 'asset'
            GROUP BY t.date, t.description, je.debit_amount, je.credit_amount
            HAVING COUNT(*) > 1
            ORDER BY t.date DESC
        """)
        result = await self._session.execute(query)
        rows = result.fetchall()

        # Collect all duplicate IDs
        all_ids: list[str] = []
        for row in rows:
            ids = row[5].split(",") if row[5] else []
            all_ids.extend(ids)
        return tuple(all_ids)

    async def find_orphan_import_ids(self) -> tuple[str, ...]:
        query = text("""
            SELECT ti.id
            FROM transaction_imports ti
            LEFT JOIN accounting_transactions t ON ti.accounting_transaction_id = t.id
            WHERE ti.accounting_transaction_id IS NOT NULL
              AND t.id IS NULL
        """)
        result = await self._session.execute(query)
        rows = result.fetchall()
        return tuple(str(row[0]) for row in rows)

    async def find_unbalanced_transaction_ids(self) -> tuple[str, ...]:
        query = text("""
            SELECT t.id
            FROM accounting_transactions t
            JOIN journal_entries je ON t.id = je.transaction_id
            GROUP BY t.id
            HAVING ABS(SUM(je.debit_amount) - SUM(je.credit_amount)) > 0.01
        """)
        result = await self._session.execute(query)
        rows = result.fetchall()
        return tuple(str(row[0]) for row in rows)

    async def delete_transactions_with_entries(
        self,
        transaction_ids: tuple[str, ...],
    ) -> int:
        if not transaction_ids:
            return 0

        # Delete journal entries first (foreign key constraint)
        await self._session.execute(
            text("DELETE FROM journal_entries WHERE transaction_id IN :ids"),
            {"ids": transaction_ids},
        )

        # Delete the transactions
        await self._session.execute(
            text("DELETE FROM accounting_transactions WHERE id IN :ids"),
            {"ids": transaction_ids},
        )

        return len(transaction_ids)

    async def delete_import_records(
        self,
        import_ids: tuple[str, ...],
    ) -> int:
        if not import_ids:
            return 0

        await self._session.execute(
            text("DELETE FROM transaction_imports WHERE id IN :ids"),
            {"ids": import_ids},
        )

        return len(import_ids)
