"""Storage for user training examples."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import numpy as np
from numpy.typing import NDArray


@dataclass
class ExampleStore:
    """Stores embeddings and labels for user's posted transactions."""

    embeddings: NDArray[np.float32] = field(
        default_factory=lambda: np.empty((0, 384), dtype=np.float32)
    )
    account_ids: list[str] = field(default_factory=list)
    account_numbers: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)

    def add(
        self,
        embedding: NDArray[np.float32],
        account_id: str,
        account_number: str,
        text: str,
    ) -> None:
        """Add a new example."""
        self.embeddings = np.vstack([self.embeddings, embedding.reshape(1, -1)])
        self.account_ids.append(account_id)
        self.account_numbers.append(account_number)
        self.texts.append(text)

    def __len__(self) -> int:
        return len(self.account_ids)

    def save(self, path: Path) -> None:
        """Save to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path.with_suffix(".npy"), self.embeddings)
        with open(path.with_suffix(".json"), "w") as f:
            json.dump(
                {
                    "account_ids": self.account_ids,
                    "account_numbers": self.account_numbers,
                    "texts": self.texts,
                },
                f,
            )

    @classmethod
    def load(cls, path: Path) -> "ExampleStore":
        """Load from disk."""
        embeddings = np.load(path.with_suffix(".npy"))
        with open(path.with_suffix(".json")) as f:
            data = json.load(f)
        return cls(
            embeddings=embeddings,
            account_ids=data["account_ids"],
            account_numbers=data["account_numbers"],
            texts=data["texts"],
        )

    @classmethod
    def load_or_empty(cls, path: Path) -> "ExampleStore":
        """Load from disk or return empty store."""
        if path.with_suffix(".npy").exists():
            return cls.load(path)
        return cls()


def get_example_path(data_dir: Path, user_id: UUID) -> Path:
    """Get path for user's example store."""
    return data_dir / "users" / str(user_id) / "examples"
