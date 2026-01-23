"""Storage for account anchor embeddings."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

import numpy as np
from numpy.typing import NDArray


@dataclass
class AnchorStore:
    """Stores embeddings for account descriptions (cold start)."""

    embeddings: NDArray[np.float32] = field(
        default_factory=lambda: np.empty((0, 384), dtype=np.float32)
    )
    account_ids: list[str] = field(default_factory=list)
    account_numbers: list[str] = field(default_factory=list)
    account_names: list[str] = field(default_factory=list)

    def set(
        self,
        embeddings: NDArray[np.float32],
        account_ids: list[str],
        account_numbers: list[str],
        account_names: list[str],
    ) -> None:
        """Set all anchors (replaces existing)."""
        self.embeddings = embeddings
        self.account_ids = account_ids
        self.account_numbers = account_numbers
        self.account_names = account_names

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
                    "account_names": self.account_names,
                },
                f,
            )

    @classmethod
    def load(cls, path: Path) -> "AnchorStore":
        """Load from disk."""
        embeddings = np.load(path.with_suffix(".npy"))
        with open(path.with_suffix(".json")) as f:
            data = json.load(f)
        return cls(
            embeddings=embeddings,
            account_ids=data["account_ids"],
            account_numbers=data["account_numbers"],
            account_names=data["account_names"],
        )

    @classmethod
    def load_or_empty(cls, path: Path) -> "AnchorStore":
        """Load from disk or return empty store."""
        if path.with_suffix(".npy").exists():
            return cls.load(path)
        return cls()


def get_anchor_path(data_dir: Path, user_id: UUID) -> Path:
    """Get path for user's anchor store."""
    return data_dir / "users" / str(user_id) / "anchors"
