"""Database initialization script."""

import asyncio
import logging
import sys

from swen.presentation.api.dependencies import create_tables, drop_tables
from swen_config.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _init_database():
    """Initialize the database and create all tables."""
    settings = get_settings()

    logger.info("Initializing database...")
    logger.info("Database URL: %s", settings.database_url)

    await create_tables()

    logger.info("Database initialized successfully!")


async def _drop_database():
    """Drop all database tables."""
    settings = get_settings()
    database_url = settings.database_url

    db_display = database_url.split("@")[-1] if "@" in database_url else database_url
    print(f"Database: {db_display}")
    print()
    print("WARNING: This will DELETE ALL DATA in the database!")
    print()
    response = input("Type 'yes' to confirm: ")
    if response.lower() != "yes":
        print("Aborted.")
        sys.exit(1)
    print()

    logger.info("Dropping all tables...")
    await drop_tables()

    logger.info("Database tables dropped successfully!")


async def _reset_database(force: bool = False):
    """Drop all tables and recreate them (USE WITH CAUTION!)."""
    settings = get_settings()
    database_url = settings.database_url

    db_display = database_url.split("@")[-1] if "@" in database_url else database_url
    print(f"Database: {db_display}")
    print()

    if not force:
        print("WARNING: This will DELETE ALL DATA in the database!")
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

    logger.info("Database recreated successfully!")


def db_init():
    """Initialize database (create tables)."""
    asyncio.run(_init_database())


def db_drop():
    """Drop all database tables."""
    asyncio.run(_drop_database())


def db_reset():
    """Drop and recreate all database tables."""
    force = "--force" in sys.argv or "-f" in sys.argv
    asyncio.run(_reset_database(force=force))
