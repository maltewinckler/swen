"""Value object representing a validated counter-account resolution result."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swen.domain.accounting.entities import Account


@dataclass(frozen=True)
class ResolvedCounterAccount:
    """A counter-account that has been resolved and validated for a transaction.

    Produced by ``CounterAccountBatchService`` after calling the proposal port
    and validating the result against business rules (account direction) and
    internal-transfer detection.

    Attributes
    ----------
    account
        The validated accounting-domain ``Account`` to use as counter-account.
    confidence
        AI confidence score (0.0-1.0), or ``None`` for fallback/internal.
    tier
        Classification tier (e.g. ``"example"``, ``"anchor"``), or ``None``
        for fallback/internal resolutions.
    """

    account: Account
    confidence: float | None = field(default=None)
