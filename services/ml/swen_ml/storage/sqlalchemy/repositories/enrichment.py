import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from swen_ml.data_models import Enrichment
from swen_ml.storage.sqlalchemy.tables import EnrichmentCacheTable


class EnrichmentRepository:
    """Repository for search enrichment cache."""

    def __init__(self, session: AsyncSession, ttl_days: int = 30):
        self._session = session
        self._ttl_days = ttl_days

    @staticmethod
    def _hash_query(query: str) -> str:
        """Create a hash key for a query."""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()

    async def get(self, query: str) -> Enrichment | None:
        """Get cached enrichment for a query."""
        query_hash = self._hash_query(query)
        now = datetime.now(UTC)

        stmt = select(EnrichmentCacheTable).where(
            EnrichmentCacheTable.query_hash == query_hash,
            EnrichmentCacheTable.expires_at > now,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return None

        # Increment hit count
        update_stmt = (
            update(EnrichmentCacheTable)
            .where(EnrichmentCacheTable.query_hash == query_hash)
            .values(hit_count=EnrichmentCacheTable.hit_count + 1)
        )
        await self._session.execute(update_stmt)
        await self._session.commit()

        # source_urls is stored as JSONB, ensure it's a list
        urls = row.source_urls if isinstance(row.source_urls, list) else []

        return Enrichment(
            query=row.query,
            enrichment_text=row.enrichment_text,
            source_urls=urls,
            created_at=row.created_at,
            expires_at=row.expires_at,
            hit_count=row.hit_count + 1,
        )

    async def set(
        self,
        query: str,
        enrichment_text: str,
        source_urls: list[str] | None = None,
    ):
        """Store enrichment in cache."""
        query_hash = self._hash_query(query)
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=self._ttl_days)

        stmt = insert(EnrichmentCacheTable).values(
            query_hash=query_hash,
            query=query,
            enrichment_text=enrichment_text,
            source_urls=source_urls,
            created_at=now,
            expires_at=expires_at,
            hit_count=0,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["query_hash"],
            set_={
                "enrichment_text": enrichment_text,
                "source_urls": source_urls,
                "expires_at": expires_at,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of deleted."""
        now = datetime.now(UTC)
        stmt = delete(EnrichmentCacheTable).where(
            EnrichmentCacheTable.expires_at <= now
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount or 0  # type: ignore[union-attr, return-value]

    async def evict_if_needed(self, max_entries: int = 10000) -> int:
        """Evict oldest entries if cache exceeds max size."""
        count_stmt = select(func.count()).select_from(EnrichmentCacheTable)
        result = await self._session.execute(count_stmt)
        current_count = result.scalar() or 0

        if current_count <= max_entries:
            return 0

        # Delete oldest entries (by created_at) to get under limit
        to_delete = current_count - max_entries

        oldest_stmt = (
            select(EnrichmentCacheTable.query_hash)
            .order_by(EnrichmentCacheTable.created_at)
            .limit(to_delete)
        )
        oldest_result = await self._session.execute(oldest_stmt)
        hashes_to_delete = [row[0] for row in oldest_result.fetchall()]

        if hashes_to_delete:
            delete_stmt = delete(EnrichmentCacheTable).where(
                EnrichmentCacheTable.query_hash.in_(hashes_to_delete)
            )
            await self._session.execute(delete_stmt)
            await self._session.commit()

        return len(hashes_to_delete)

    async def stats(self) -> dict[str, int]:
        """Get cache statistics."""
        count_stmt = select(func.count()).select_from(EnrichmentCacheTable)
        result = await self._session.execute(count_stmt)
        total = result.scalar() or 0

        hits_stmt = select(func.sum(EnrichmentCacheTable.hit_count))
        hits_result = await self._session.execute(hits_stmt)
        total_hits = hits_result.scalar() or 0

        return {"entries": total, "total_hits": total_hits}

    async def clear(self) -> int:
        """Clear all cache entries. Returns count of deleted."""
        stmt = delete(EnrichmentCacheTable)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount or 0  # type: ignore[union-attr, return-value]
