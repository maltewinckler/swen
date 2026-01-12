"""SQLAlchemy analytics adapters (read side).

These are infrastructure implementations of application-layer analytics ports.
"""

from swen.infrastructure.persistence.sqlalchemy.adapters.analytics.sqlalchemy_analytics_read_adapter import (
    SqlAlchemyAnalyticsReadAdapter,
)

__all__ = ["SqlAlchemyAnalyticsReadAdapter"]


