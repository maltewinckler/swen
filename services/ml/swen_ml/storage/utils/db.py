"""Database management utilities for ML service."""

import asyncio
import logging
import sys

from swen_ml.config.settings import get_settings

# Import tables to register with Base.metadata
from swen_ml.storage.sqlalchemy import tables  # noqa: F401
from swen_ml.storage.sqlalchemy.base import Base
from swen_ml.storage.sqlalchemy.engine import get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables() -> None:
    """Create all database tables (idempotent)."""
    engine = get_engine()
    logger.info("Ensuring all database tables exist...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    logger.info("Database schema is up to date")


async def drop_tables() -> None:
    """Drop all database tables and indexes."""
    from sqlalchemy import text

    engine = get_engine()
    logger.warning("Dropping all database tables...")

    async with engine.begin() as conn:
        # Drop all tables, indexes, and constraints by dropping the public schema
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))

    await engine.dispose()
    logger.info("Database tables dropped successfully")


async def _reset_database(force: bool = False) -> None:
    """Drop all tables and recreate them."""
    settings = get_settings()
    database_url = settings.database_url

    db_display = database_url.split("@")[-1] if "@" in database_url else database_url
    print(f"ML Database: {db_display}")
    print()

    if not force:
        print("WARNING: This will DELETE ALL ML DATA!")
        print()
        response = input("Type 'yes' to confirm: ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(1)
        print()

    logger.info("Dropping all tables...")
    await drop_tables()

    logger.info("Creating all tables...")
    await create_tables()

    logger.info("ML database recreated successfully!")


def db_init():
    """Initialize database (create tables)."""
    asyncio.run(create_tables())


def db_reset():
    """Drop and recreate all database tables."""
    force = "--force" in sys.argv or "-f" in sys.argv
    asyncio.run(_reset_database(force=force))
