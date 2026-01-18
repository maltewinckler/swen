"""Per-user embedding storage using NPZ files."""

import json
import logging
import shutil
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID

import numpy as np
from filelock import FileLock
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class EmbeddingStore:
    """Manages per-user embedding storage."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _user_dir(self, user_id: UUID) -> Path:
        return self.base_path / str(user_id)

    def _ensure_user_dir(self, user_id: UUID) -> Path:
        user_dir = self._user_dir(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    @contextmanager
    def _user_lock(self, user_id: UUID) -> Iterator[None]:
        """Acquire file lock for concurrent access safety."""
        user_dir = self._ensure_user_dir(user_id)
        lock = FileLock(user_dir / ".lock", timeout=10)
        try:
            with lock:
                yield
        except Exception:
            logger.warning("Failed to acquire lock for user %s", user_id)
            raise

    # Account embeddings

    def load_account_embeddings(self, user_id: UUID) -> dict[UUID, NDArray[np.float32]]:
        path = self._user_dir(user_id) / "accounts.npz"
        if not path.exists():
            return {}
        try:
            data = np.load(path)
            return {UUID(k): v for k, v in data.items()}
        except Exception as e:
            logger.warning("Failed to load account embeddings: %s", e)
            return {}

    def save_account_embeddings(
        self, user_id: UUID, embeddings: dict[UUID, NDArray[np.float32]]
    ) -> None:
        user_dir = self._ensure_user_dir(user_id)
        np.savez(
            user_dir / "accounts.npz",
            **{str(k): v for k, v in embeddings.items()},  # type: ignore[arg-type]
        )

    def update_account_embedding(
        self, user_id: UUID, account_id: UUID, embedding: NDArray[np.float32]
    ) -> None:
        with self._user_lock(user_id):
            embeddings = self.load_account_embeddings(user_id)
            embeddings[account_id] = embedding
            self.save_account_embeddings(user_id, embeddings)

    # Transaction embeddings

    def load_transaction_embeddings(
        self, user_id: UUID
    ) -> dict[UUID, NDArray[np.float32]]:
        path = self._user_dir(user_id) / "posted_transactions.npz"
        if not path.exists():
            return {}
        try:
            data = np.load(path)
            return {UUID(k): v for k, v in data.items()}
        except Exception as e:
            logger.warning("Failed to load transaction embeddings: %s", e)
            return {}

    def _save_transaction_embeddings(
        self, user_id: UUID, embeddings: dict[UUID, NDArray[np.float32]]
    ) -> None:
        user_dir = self._ensure_user_dir(user_id)
        np.savez(
            user_dir / "posted_transactions.npz",
            **{str(k): v for k, v in embeddings.items()},  # type: ignore[arg-type]
        )

    # Transaction texts (for explainability)

    def load_texts(self, user_id: UUID) -> dict[str, list[str]]:
        path = self._user_dir(user_id) / "transaction_texts.json"
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load transaction texts: %s", e)
            return {}

    def _save_texts(self, user_id: UUID, texts: dict[str, list[str]]) -> None:
        user_dir = self._ensure_user_dir(user_id)
        with open(user_dir / "transaction_texts.json", "w") as f:
            json.dump(texts, f)

    # Transaction IDs (for deduplication)

    def _load_transaction_ids(self, user_id: UUID) -> dict[str, list[str]]:
        path = self._user_dir(user_id) / "transaction_ids.json"
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load transaction IDs: %s", e)
            return {}

    def _save_transaction_ids(self, user_id: UUID, ids: dict[str, list[str]]) -> None:
        user_dir = self._ensure_user_dir(user_id)
        with open(user_dir / "transaction_ids.json", "w") as f:
            json.dump(ids, f)

    def has_transaction_id(
        self, user_id: UUID, account_id: UUID, transaction_id: UUID
    ) -> bool:
        ids = self._load_transaction_ids(user_id)
        return str(transaction_id) in ids.get(str(account_id), [])

    def get_example_count(self, user_id: UUID, account_id: UUID) -> int:
        embeddings = self.load_transaction_embeddings(user_id)
        acc_emb = embeddings.get(account_id)
        return acc_emb.shape[0] if acc_emb is not None else 0

    # Metadata

    def load_metadata(self, user_id: UUID) -> dict:
        path = self._user_dir(user_id) / "metadata.json"
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load metadata: %s", e)
            return {}

    def save_metadata(self, user_id: UUID, metadata: dict) -> None:
        user_dir = self._ensure_user_dir(user_id)
        with open(user_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)

    def update_metadata(
        self, user_id: UUID, model_name: str, embedding_dim: int
    ) -> None:
        with self._user_lock(user_id):
            metadata = self.load_metadata(user_id)
            metadata["model_id"] = model_name
            metadata["embedding_dim"] = embedding_dim
            metadata["last_updated"] = datetime.now(timezone.utc).isoformat()

            acc_emb = self.load_account_embeddings(user_id)
            txn_emb = self.load_transaction_embeddings(user_id)
            metadata["account_count"] = len(acc_emb)
            metadata["transaction_count"] = sum(v.shape[0] for v in txn_emb.values())

            self.save_metadata(user_id, metadata)

    # Combined operations

    def add_transaction_embedding(
        self,
        user_id: UUID,
        account_id: UUID,
        embedding: NDArray[np.float32],
        text: str,
        max_examples: int = 100,
        transaction_id: UUID | None = None,
    ) -> int:
        """Add embedding. Returns total examples for this account."""
        with self._user_lock(user_id):
            embeddings = self.load_transaction_embeddings(user_id)
            texts = self.load_texts(user_id)
            txn_ids = self._load_transaction_ids(user_id)

            acc_key_str = str(account_id)

            if account_id in embeddings:
                embeddings[account_id] = np.vstack([embeddings[account_id], embedding])
                texts.setdefault(acc_key_str, []).append(text)
            else:
                embeddings[account_id] = embedding.reshape(1, -1)
                texts[acc_key_str] = [text]

            if transaction_id is not None:
                txn_ids.setdefault(acc_key_str, []).append(str(transaction_id))

            # Prune old examples
            if embeddings[account_id].shape[0] > max_examples:
                embeddings[account_id] = embeddings[account_id][-max_examples:]
                texts[acc_key_str] = texts[acc_key_str][-max_examples:]
                if acc_key_str in txn_ids:
                    txn_ids[acc_key_str] = txn_ids[acc_key_str][-max_examples:]

            self._save_transaction_embeddings(user_id, embeddings)
            self._save_texts(user_id, texts)
            if transaction_id is not None:
                self._save_transaction_ids(user_id, txn_ids)

            return embeddings[account_id].shape[0]

    def delete_account(self, user_id: UUID, account_id: UUID) -> int:
        """Delete account embeddings. Returns number of examples deleted."""
        with self._user_lock(user_id):
            acc_key_str = str(account_id)
            user_dir = self._user_dir(user_id)

            # Account embeddings
            acc_embeddings = self.load_account_embeddings(user_id)
            acc_embeddings.pop(account_id, None)
            if acc_embeddings:
                self.save_account_embeddings(user_id, acc_embeddings)
            elif (p := user_dir / "accounts.npz").exists():
                p.unlink()

            # Transaction embeddings
            txn_embeddings = self.load_transaction_embeddings(user_id)
            deleted_arr = txn_embeddings.pop(account_id, None)
            deleted_count = deleted_arr.shape[0] if deleted_arr is not None else 0

            if txn_embeddings:
                self._save_transaction_embeddings(user_id, txn_embeddings)
            elif (p := user_dir / "posted_transactions.npz").exists():
                p.unlink()

            # Texts
            texts = self.load_texts(user_id)
            texts.pop(acc_key_str, None)
            if texts:
                self._save_texts(user_id, texts)
            elif (p := user_dir / "transaction_texts.json").exists():
                p.unlink()

            # Transaction IDs
            txn_ids = self._load_transaction_ids(user_id)
            txn_ids.pop(acc_key_str, None)
            if txn_ids:
                self._save_transaction_ids(user_id, txn_ids)
            elif (p := user_dir / "transaction_ids.json").exists():
                p.unlink()

            return deleted_count

    def delete_user(self, user_id: UUID) -> tuple[int, int]:
        """Delete all user data. Returns (accounts_deleted, examples_deleted)."""
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return 0, 0

        acc_count = len(self.load_account_embeddings(user_id))
        txn_embeddings = self.load_transaction_embeddings(user_id)
        txn_count = sum(v.shape[0] for v in txn_embeddings.values())

        shutil.rmtree(user_dir)
        return acc_count, txn_count

    def get_storage_size(self, user_id: UUID) -> int:
        user_dir = self._user_dir(user_id)
        if not user_dir.exists():
            return 0
        return sum(f.stat().st_size for f in user_dir.iterdir() if f.is_file())

    def list_users(self) -> list[UUID]:
        users = []
        for path in self.base_path.iterdir():
            if path.is_dir():
                try:
                    users.append(UUID(path.name))
                except ValueError:
                    pass
        return users
