"""Analytics ports (read side).

These ports are report-like: one method per report/query.
They intentionally return application DTOs (read models), not domain aggregates.
"""

from swen.application.ports.analytics.analytics_read_port import AnalyticsReadPort

__all__ = ["AnalyticsReadPort"]
