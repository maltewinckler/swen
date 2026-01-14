"""SQLAlchemy declarative base for swen_identity models.

Uses the same metadata as swen's Base to allow cross-module foreign keys.
"""

from swen.infrastructure.persistence.sqlalchemy.models.base import Base

# Use the same metadata as swen's Base to allow FK references across modules
IdentityBase = Base
