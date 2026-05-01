from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swen_ml.inference.classification.context import (
        EmbeddingStore,
        TransactionContext,
    )

logger = logging.getLogger(__name__)


class BaseClassifier(ABC):
    """Base classifier implementing direction-aware bucketing.

    Subclasses must implement:
    - ``_embedding_store`` (property): which store to draw candidates from
    - ``_build_text``: how to build the query text from a context
    - ``_classify_group``: the core similarity/decision logic

    Subclasses may override:
    - ``_on_empty_direction_store``: hook called when the direction-filtered
      store is empty (default: no-op; ExampleClassifier uses it to
      pre-compute and cache embeddings for the anchor tier).
    """

    name: str
    accept_threshold: float

    @property
    @abstractmethod
    def _embedding_store(self) -> EmbeddingStore:
        """The embedding store for this classifier tier."""

    @abstractmethod
    def _build_text(self, ctx: TransactionContext) -> str:
        """Build the query text used for similarity lookup."""

    @abstractmethod
    def _classify_group(
        self,
        group: list[TransactionContext],
        store: EmbeddingStore,
    ) -> int:
        """Classify a same-direction group against a direction-filtered store.

        Returns the number of newly resolved transactions.
        """

    def _on_empty_direction_store(
        self,
        group: list[TransactionContext],
        is_debit: bool,
    ) -> None:
        """Hook called when the direction-filtered store is empty.

        Default: no-op.  Override to e.g. pre-compute embeddings for
        downstream tiers.
        """

    async def classify_batch(self, contexts: list[TransactionContext]) -> None:
        store = self._embedding_store
        if len(store) == 0:
            logger.debug("%s: no embeddings available", self.name)
            return

        unresolved = [ctx for ctx in contexts if not ctx.resolved]
        if not unresolved:
            return

        # Bucket by transaction direction so that we only match against
        # account types that are valid as a counter-account for the given
        # direction (double-entry direction policy).
        debit_ctxs = [c for c in unresolved if c.amount < 0]
        credit_ctxs = [c for c in unresolved if c.amount >= 0]

        n_total = 0
        for is_debit, group in ((True, debit_ctxs), (False, credit_ctxs)):
            if not group:
                continue
            filtered = store.filter_for_direction(is_debit)
            if len(filtered) == 0:
                logger.debug(
                    "%s: no %s-side embeddings available; leaving %d transactions for downstream",
                    self.name,
                    "expense" if is_debit else "income",
                    len(group),
                )
                self._on_empty_direction_store(group, is_debit)
                continue
            n_total += self._classify_group(group, filtered)

        logger.debug(
            "%s: %d/%d resolved (threshold=%.2f)",
            self.name,
            n_total,
            len(unresolved),
            self.accept_threshold,
        )
