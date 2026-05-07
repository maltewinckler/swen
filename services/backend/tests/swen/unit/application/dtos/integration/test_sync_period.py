"""Tests for the `SyncPeriod` frozen value object."""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from swen.application.dtos.integration import SyncPeriod


class TestSyncPeriodImmutability:
    def test_attribute_assignment_raises_frozen_instance_error(self):
        period = SyncPeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            adaptive=False,
        )

        with pytest.raises(FrozenInstanceError):
            period.start_date = date(2025, 2, 1)  # type: ignore[misc]


class TestSyncPeriodWiden:
    def test_widen_returns_self_when_not_adaptive(self):
        period = SyncPeriod(
            start_date=date(2025, 1, 10),
            end_date=date(2025, 1, 20),
            adaptive=False,
        )

        widened = period.widen(date(2025, 1, 1), date(2025, 1, 31))

        assert widened is period

    def test_widen_expands_window_when_adaptive(self):
        period = SyncPeriod(
            start_date=date(2025, 1, 10),
            end_date=date(2025, 1, 20),
            adaptive=True,
        )

        widened = period.widen(date(2025, 1, 1), date(2025, 1, 31))

        assert widened is not period
        assert widened.start_date == date(2025, 1, 1)
        assert widened.end_date == date(2025, 1, 31)
        assert widened.adaptive is True

    def test_widen_keeps_existing_bounds_when_observed_range_is_narrower(self):
        period = SyncPeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            adaptive=True,
        )

        widened = period.widen(date(2025, 1, 10), date(2025, 1, 20))

        assert widened.start_date == date(2025, 1, 1)
        assert widened.end_date == date(2025, 1, 31)
        assert widened.adaptive is True

    def test_widen_mixes_existing_and_observed_bounds(self):
        period = SyncPeriod(
            start_date=date(2025, 1, 5),
            end_date=date(2025, 1, 25),
            adaptive=True,
        )

        widened = period.widen(date(2025, 1, 1), date(2025, 1, 20))

        assert widened.start_date == date(2025, 1, 1)
        assert widened.end_date == date(2025, 1, 25)
