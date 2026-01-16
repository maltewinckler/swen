"""Fixtures for security isolation tests.

These tests need dynamically created users (Alice and Bob) to verify
that user isolation is working correctly.
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest_asyncio

from swen_identity.infrastructure.persistence.sqlalchemy.models import UserModel

# Define fixed UUIDs for Alice and Bob that match the test file
# These must be seeded BEFORE the test file imports create the User objects
ALICE_UUID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
BOB_UUID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest_asyncio.fixture(scope="function", autouse=True)
async def seed_alice_and_bob(db_session):
    """Automatically seed Alice and Bob users for all security tests.

    This fixture runs before each test to ensure Alice and Bob exist
    in the database, satisfying FK constraints.
    """
    # Import here to get the actual UUIDs used by the test file
    from tests.cross_domain.integration.security.test_user_data_isolation import (
        USER_ALICE,
        USER_BOB,
    )

    now = datetime.now(tz=timezone.utc)

    # Check if users already exist (from db_session fixture seeding)
    existing_alice = await db_session.get(UserModel, USER_ALICE.id)
    existing_bob = await db_session.get(UserModel, USER_BOB.id)

    if not existing_alice:
        alice_model = UserModel(
            id=USER_ALICE.id,
            email=USER_ALICE.email,
            role="user",
            created_at=now,
            updated_at=now,
        )
        db_session.add(alice_model)

    if not existing_bob:
        bob_model = UserModel(
            id=USER_BOB.id,
            email=USER_BOB.email,
            role="user",
            created_at=now,
            updated_at=now,
        )
        db_session.add(bob_model)

    await db_session.commit()
