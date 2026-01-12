"""SQLAlchemy declarative base for swen_auth models.

This provides a separate Base for auth models. The consuming application
should include AuthBase.metadata in its migration configuration.

Examples
--------
# In Alembic env.py:
from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen_auth.persistence.sqlalchemy import AuthBase

# Combine metadata for migrations
target_metadata = Base.metadata
# AuthBase tables will be included if models are imported
"""

from sqlalchemy.orm import DeclarativeBase


class AuthBase(DeclarativeBase):
    """Declarative base for swen_auth models.

    Note: For applications using a single database, you may want to
    configure AuthBase to use the same metadata as your main Base.
    This can be done by setting AuthBase.metadata = YourBase.metadata
    before importing models.
    """
