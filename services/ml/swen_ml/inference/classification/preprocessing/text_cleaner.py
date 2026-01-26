from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from swen_ml.inference.classification.context import (
        PipelineContext,
        TransactionContext,
    )
    from swen_ml.storage import NoiseRepository

# Payment providers to strip from counterparty
PAYMENT_PROVIDERS = {"PAYPAL", "SUMUP", "ZETTLE", "STRIPE", "KLARNA"}

# Pattern for tokenizing text
TOKEN_PATTERN = re.compile(r"[a-zA-ZäöüÄÖÜß]+")


def clean_counterparty(counterparty: str | None) -> str | None:
    """Strip payment providers and normalize separators.

    This is a standalone function for use outside the pipeline context.
    """
    if not counterparty:
        return None

    text = counterparty.strip()
    upper = text.upper()

    # Strip payment provider prefixes
    for provider in PAYMENT_PROVIDERS:
        if upper.startswith(provider):
            text = re.sub(rf"^{provider}[./*]*", "", text, flags=re.IGNORECASE)
            break

    # Convert separators to spaces
    text = re.sub(r"[./*]+", " ", text)

    # Clean up whitespace
    text = " ".join(text.split())

    return text if text else None


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    return [m.group().lower() for m in TOKEN_PATTERN.finditer(text)]


@dataclass
class NoiseModel:
    """IDF-based noise detection for purpose text.

    Learns which tokens are boilerplate for a user's bank by tracking
    document frequency. Tokens appearing in >threshold of transactions
    are considered noise (e.g., "VISA", "Kartenzahlung").
    """

    doc_count: int = 0
    token_doc_freq: Counter[str] = field(default_factory=Counter)
    _noise_cache: set[str] | None = field(default=None, repr=False)

    def observe_batch(self, texts: list[str]):
        for text in texts:
            tokens = set(tokenize(text))
            self.token_doc_freq.update(tokens)

        self.doc_count += len(texts)
        self._noise_cache = None  # Invalidate cache

    def get_noise_tokens(self, threshold: float = 0.30) -> set[str]:
        if self._noise_cache is not None:
            return self._noise_cache

        if self.doc_count == 0:
            return set()

        cutoff = int(self.doc_count * threshold)
        self._noise_cache = {
            token for token, freq in self.token_doc_freq.items() if freq > cutoff
        }
        return self._noise_cache

    def clean(self, text: str, threshold: float = 0.30) -> str:
        noise = self.get_noise_tokens(threshold)
        tokens = tokenize(text)
        informative = [t for t in tokens if t not in noise]
        return " ".join(informative)

    def clean_batch(self, texts: list[str], threshold: float = 0.30) -> list[str]:
        noise = self.get_noise_tokens(threshold)
        return [" ".join(t for t in tokenize(text) if t not in noise) for text in texts]

    def to_dict(self) -> dict:
        return {
            "doc_count": self.doc_count,
            "token_doc_freq": dict(self.token_doc_freq),
        }

    @classmethod
    def from_dict(cls, data: dict) -> NoiseModel:
        return cls(
            doc_count=data["doc_count"],
            token_doc_freq=Counter(data["token_doc_freq"]),
        )

    @classmethod
    async def from_repository(cls, repo: NoiseRepository) -> NoiseModel:
        data = await repo.get()
        if data:
            return cls.from_dict(
                {
                    "token_doc_freq": data.token_frequencies,
                    "doc_count": data.document_count,
                }
            )
        return cls()


class TextCleaner:
    """Preprocessor that cleans counterparty and purpose text."""

    name = "text_cleaner"

    def __init__(self, pipeline_ctx: PipelineContext, noise_threshold: float = 0.30):
        self._noise_model = pipeline_ctx.noise_model
        self._noise_threshold = noise_threshold

    def clean_purpose(self, purpose: str) -> str:
        return self._noise_model.clean(purpose, self._noise_threshold)

    def process_batch(self, contexts: list[TransactionContext]):
        for ctx in contexts:
            ctx.cleaned_counterparty = clean_counterparty(ctx.raw_counterparty)
            ctx.cleaned_purpose = self.clean_purpose(ctx.raw_purpose)
