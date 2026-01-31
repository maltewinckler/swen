from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from swen_ml.inference.classification.context import (
        PipelineContext,
        TransactionContext,
    )

from swen_ml.inference.classification.context import ClassificationMatch

logger = logging.getLogger(__name__)


class ExampleClassifier:
    """Classifier that matches transactions against user's historical examples."""

    name = "example"

    def __init__(
        self,
        pipeline_ctx: PipelineContext,
        high_confidence: float = 0.85,
        accept_threshold: float = 0.70,
        margin_threshold: float = 0.10,
    ):
        self.pipeline_ctx = pipeline_ctx
        self.high_confidence = high_confidence
        self.accept_threshold = accept_threshold
        self.margin_threshold = margin_threshold

    def _build_text(self, ctx: TransactionContext) -> str:
        # different from anchor's _build_text: no enrichment here
        parts = []
        if ctx.cleaned_counterparty:
            parts.append(ctx.cleaned_counterparty)
        if ctx.cleaned_purpose:
            parts.append(ctx.cleaned_purpose)
        return " ".join(parts)

    async def classify_batch(
        self,
        contexts: list[TransactionContext],
    ):
        examples = self.pipeline_ctx.example_store

        if len(examples) == 0:
            logger.debug("Example classifier: no examples available")
            return

        unresolved = [ctx for ctx in contexts if not ctx.resolved]
        if not unresolved:
            return

        # Build texts and compute embeddings
        texts = [self._build_text(ctx) for ctx in unresolved]
        embeddings = self.pipeline_ctx.encoder.encode(texts)

        # Compute similarities: (N, dim) @ (M, dim).T = (N, M)
        similarities = embeddings @ examples.embeddings.T

        # Get top-2 for margin computation
        top2_idx = np.argsort(-similarities, axis=1)[:, :2]
        rows = np.arange(len(unresolved))
        top1_scores = similarities[rows, top2_idx[:, 0]]

        if similarities.shape[1] > 1:
            top2_scores = similarities[rows, top2_idx[:, 1]]
        else:
            top2_scores = np.zeros_like(top1_scores)

        margins = top1_scores - top2_scores

        # Apply decision logic
        high_conf = top1_scores >= self.high_confidence
        clear_winner = (top1_scores >= self.accept_threshold) & (
            margins >= self.margin_threshold
        )
        accept = high_conf | clear_winner

        # Update contexts
        n_resolved = 0
        for i, ctx in enumerate(unresolved):
            # Store embeddings in context for later use
            ctx.embedding = embeddings[i]

            if accept[i]:
                best_idx = int(top2_idx[i, 0])
                ctx.example_match = ClassificationMatch(
                    account_id=examples.account_ids[best_idx],
                    account_number=examples.account_numbers[best_idx],
                    confidence=float(top1_scores[i]),
                )
                ctx.resolved = True
                ctx.resolved_by = self.name
                n_resolved += 1

        logger.debug(
            "Example classifier: %d/%d resolved (threshold=%.2f)",
            n_resolved,
            len(unresolved),
            self.accept_threshold,
        )
