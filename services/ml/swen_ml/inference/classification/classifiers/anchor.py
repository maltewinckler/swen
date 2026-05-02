from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from swen_ml.inference.classification.context import (
        EmbeddingStore,
        PipelineContext,
        TransactionContext,
    )

from swen_ml.inference.classification.classifiers.base import BaseClassifier
from swen_ml.inference.classification.context import ClassificationMatch

logger = logging.getLogger(__name__)


class AnchorClassifier(BaseClassifier):
    """Classifier that matches transactions against account description embeddings."""

    name = "anchor"

    def __init__(self, pipeline_ctx: PipelineContext, accept_threshold: float = 0.55):
        self.pipeline_ctx = pipeline_ctx
        self.accept_threshold = accept_threshold

    @property
    def _embedding_store(self) -> EmbeddingStore:
        return self.pipeline_ctx.anchor_store

    def _build_text(self, ctx: TransactionContext) -> str:
        parts = []
        if ctx.cleaned_counterparty:
            parts.append(ctx.cleaned_counterparty)
        if ctx.cleaned_purpose:
            parts.append(ctx.cleaned_purpose)
        if ctx.search_enrichment:
            parts.append(ctx.search_enrichment)
        return " ".join(parts)

    def _classify_group(
        self,
        group: list[TransactionContext],
        store: EmbeddingStore,
    ) -> int:
        # Build texts (with enrichment) and compute embeddings
        texts = [self._build_text(ctx) for ctx in group]
        embeddings = self.pipeline_ctx.encoder.encode(texts)

        # Compute similarities and find best matches
        similarities = embeddings @ store.embeddings.T
        best_idx = np.argmax(similarities, axis=1)
        best_scores = np.max(similarities, axis=1)
        accept = best_scores >= self.accept_threshold

        n_resolved = 0
        for i, ctx in enumerate(group):
            # Store enriched embeddings
            ctx.enriched_embedding = embeddings[i]
            anchor_idx = int(best_idx[i])
            score = float(best_scores[i])
            best_account = store.account_numbers[anchor_idx]

            text_preview = texts[i][:100] + "[...]" if len(texts[i]) > 100 else texts[i]
            logger.debug(
                "  TX %s -> best=%s score=%.3f %s (txt: %s)",
                ctx.cleaned_counterparty,
                best_account,
                score,
                "✓" if accept[i] else "",
                text_preview,
            )

            if accept[i]:
                ctx.anchor_match = ClassificationMatch(
                    account_id=store.account_ids[anchor_idx],
                    account_number=best_account,
                    confidence=score,
                )
                ctx.resolved = True
                ctx.resolved_by = self.name
                n_resolved += 1

        return n_resolved
