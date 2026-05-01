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


class ExampleClassifier(BaseClassifier):
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

    @property
    def _embedding_store(self) -> EmbeddingStore:
        return self.pipeline_ctx.example_store

    def _build_text(self, ctx: TransactionContext) -> str:
        # no enrichment here — match the raw text stored as a training example
        parts = []
        if ctx.cleaned_counterparty:
            parts.append(ctx.cleaned_counterparty)
        if ctx.cleaned_purpose:
            parts.append(ctx.cleaned_purpose)
        return " ".join(parts)

    def _on_empty_direction_store(
        self,
        group: list[TransactionContext],
        is_debit: bool,
    ) -> None:
        # Pre-compute and cache embeddings so the anchor tier can reuse them.
        texts = [self._build_text(ctx) for ctx in group]
        embeddings = self.pipeline_ctx.encoder.encode(texts)
        for ctx, emb in zip(group, embeddings):
            ctx.embedding = emb

    def _classify_group(
        self,
        group: list[TransactionContext],
        store: EmbeddingStore,
    ) -> int:
        # Build texts and compute embeddings
        texts = [self._build_text(ctx) for ctx in group]
        embeddings = self.pipeline_ctx.encoder.encode(texts)

        # Compute similarities: (N, dim) @ (M, dim).T = (N, M)
        similarities = embeddings @ store.embeddings.T

        # Get top-2 for margin computation
        top2_idx = np.argsort(-similarities, axis=1)[:, :2]
        rows = np.arange(len(group))
        top1_scores = similarities[rows, top2_idx[:, 0]]

        if similarities.shape[1] > 1:
            top2_scores = similarities[rows, top2_idx[:, 1]]
        else:
            top2_scores = np.zeros_like(top1_scores)

        margins = top1_scores - top2_scores

        # Apply decision logic
        high_conf = top1_scores >= self.high_confidence
        clear_winner = (top1_scores >= self.accept_threshold) & (margins >= self.margin_threshold)
        accept = high_conf | clear_winner

        # Update contexts
        n_resolved = 0
        for i, ctx in enumerate(group):
            # Store embeddings in context for later use
            ctx.embedding = embeddings[i]

            if accept[i]:
                best_idx = int(top2_idx[i, 0])
                ctx.example_match = ClassificationMatch(
                    account_id=store.account_ids[best_idx],
                    account_number=store.account_numbers[best_idx],
                    confidence=float(top1_scores[i]),
                )
                ctx.resolved = True
                ctx.resolved_by = self.name
                n_resolved += 1

        return n_resolved
