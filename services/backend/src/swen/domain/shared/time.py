"""Time utilities for the domain layer."""

from datetime import date, datetime, timezone


def utc_now() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(tz=timezone.utc)


def today_utc() -> date:
    """Return current date in UTC (timezone-aware)."""
    return datetime.now(tz=timezone.utc).date()


def ensure_tz_aware(dt: datetime) -> datetime:
    """Ensure datetime is timezone-aware (UTC if naive)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
