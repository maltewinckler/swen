"""Adaptive noise model for boilerplate detection."""

import re
from collections import Counter
from dataclasses import dataclass, field

# Simple tokenizer for German transaction texts
TOKEN_PATTERN = re.compile(r"[a-zA-ZäöüÄÖÜß]+")


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    return [m.group().lower() for m in TOKEN_PATTERN.finditer(text)]


@dataclass
class NoiseModel:
    """Learn which tokens are boilerplate for a user's bank."""

    doc_count: int = 0
    token_doc_freq: Counter = field(default_factory=Counter)
    _noise_cache: set[str] | None = field(default=None, repr=False)

    def observe_batch(self, texts: list[str]) -> None:
        """Observe all transaction texts at once."""
        for text in texts:
            tokens = set(tokenize(text))
            self.token_doc_freq.update(tokens)

        self.doc_count += len(texts)
        self._noise_cache = None  # Invalidate cache

    def get_noise_tokens(self, threshold: float = 0.30) -> set[str]:
        """Get tokens that appear in more than threshold of documents."""
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
        """Remove noise tokens from text."""
        noise = self.get_noise_tokens(threshold)
        tokens = tokenize(text)
        informative = [t for t in tokens if t not in noise]
        return " ".join(informative)

    def clean_batch(self, texts: list[str], threshold: float = 0.30) -> list[str]:
        """Remove noise tokens from all texts."""
        noise = self.get_noise_tokens(threshold)
        return [
            " ".join(t for t in tokenize(text) if t not in noise) for text in texts
        ]

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "doc_count": self.doc_count,
            "token_doc_freq": dict(self.token_doc_freq),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NoiseModel":
        """Deserialize from dictionary."""
        return cls(
            doc_count=data["doc_count"],
            token_doc_freq=Counter(data["token_doc_freq"]),
        )
