"""Tests for EmbeddingStore."""

from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest

from swen_ml.storage.embedding_store import EmbeddingStore


class TestEmbeddingStore:
    """Tests for EmbeddingStore."""

    def test_add_transaction_embedding(self, temp_storage_path: Path) -> None:
        """Test adding transaction embeddings."""
        store = EmbeddingStore(temp_storage_path)
        user_id = uuid4()
        account_id = uuid4()

        embedding = np.random.rand(512).astype(np.float32)
        total = store.add_transaction_embedding(
            user_id=user_id,
            account_id=account_id,
            embedding=embedding,
            text="Test transaction",
        )

        assert total == 1

        # Add another
        total = store.add_transaction_embedding(
            user_id=user_id,
            account_id=account_id,
            embedding=np.random.rand(512).astype(np.float32),
            text="Another transaction",
        )

        assert total == 2

        # Load and verify
        embeddings = store.load_transaction_embeddings(user_id)
        assert account_id in embeddings
        assert embeddings[account_id].shape == (2, 512)

        texts = store.load_texts(user_id)
        assert str(account_id) in texts
        assert len(texts[str(account_id)]) == 2

    def test_pruning(self, temp_storage_path: Path) -> None:
        """Test that examples are pruned when max_examples is reached."""
        store = EmbeddingStore(temp_storage_path)
        user_id = uuid4()
        account_id = uuid4()

        # Add more than max_examples
        max_examples = 5
        for i in range(10):
            store.add_transaction_embedding(
                user_id=user_id,
                account_id=account_id,
                embedding=np.random.rand(512).astype(np.float32),
                text=f"Transaction {i}",
                max_examples=max_examples,
            )

        embeddings = store.load_transaction_embeddings(user_id)
        assert embeddings[account_id].shape[0] == max_examples

        texts = store.load_texts(user_id)
        assert len(texts[str(account_id)]) == max_examples
        # Should keep most recent (5-9)
        assert texts[str(account_id)][0] == "Transaction 5"
        assert texts[str(account_id)][-1] == "Transaction 9"

    def test_delete_account(self, temp_storage_path: Path) -> None:
        """Test deleting an account's embeddings."""
        store = EmbeddingStore(temp_storage_path)
        user_id = uuid4()
        account_id_1 = uuid4()
        account_id_2 = uuid4()

        # Add transaction embeddings for two accounts
        for acc_id in [account_id_1, account_id_2]:
            store.add_transaction_embedding(
                user_id=user_id,
                account_id=acc_id,
                embedding=np.random.rand(512).astype(np.float32),
                text=f"Test for {acc_id}",
            )

        # Delete first account
        deleted = store.delete_account(user_id, account_id_1)
        assert deleted == 1

        # Verify first is gone, second remains
        txn_emb = store.load_transaction_embeddings(user_id)
        assert account_id_1 not in txn_emb
        assert account_id_2 in txn_emb

    def test_delete_user(self, temp_storage_path: Path) -> None:
        """Test deleting all user data."""
        store = EmbeddingStore(temp_storage_path)
        user_id = uuid4()
        account_id = uuid4()

        # Add transaction data
        store.add_transaction_embedding(
            user_id=user_id,
            account_id=account_id,
            embedding=np.random.rand(512).astype(np.float32),
            text="Test",
        )

        # Delete user
        acc_deleted, txn_deleted = store.delete_user(user_id)
        assert acc_deleted == 1  # 1 account with examples
        assert txn_deleted == 1

        # Verify directory is gone
        assert not store._user_dir(user_id).exists()

    def test_list_users(self, temp_storage_path: Path) -> None:
        """Test listing users."""
        store = EmbeddingStore(temp_storage_path)
        user_ids = [uuid4() for _ in range(3)]

        for user_id in user_ids:
            store.add_transaction_embedding(
                user_id=user_id,
                account_id=uuid4(),
                embedding=np.random.rand(512).astype(np.float32),
                text="Test",
            )

        listed = store.list_users()
        assert len(listed) == 3
        assert set(listed) == set(user_ids)

    def test_transaction_id_deduplication(self, temp_storage_path: Path) -> None:
        """Test transaction ID tracking for deduplication."""
        store = EmbeddingStore(temp_storage_path)
        user_id = uuid4()
        account_id = uuid4()
        transaction_id = uuid4()

        # First add
        store.add_transaction_embedding(
            user_id=user_id,
            account_id=account_id,
            embedding=np.random.rand(512).astype(np.float32),
            text="Test",
            transaction_id=transaction_id,
        )

        # Check deduplication
        assert store.has_transaction_id(user_id, account_id, transaction_id)
        assert not store.has_transaction_id(user_id, account_id, uuid4())

    def test_get_example_count(self, temp_storage_path: Path) -> None:
        """Test getting example count for an account."""
        store = EmbeddingStore(temp_storage_path)
        user_id = uuid4()
        account_id = uuid4()

        assert store.get_example_count(user_id, account_id) == 0

        store.add_transaction_embedding(
            user_id=user_id,
            account_id=account_id,
            embedding=np.random.rand(512).astype(np.float32),
            text="Test",
        )

        assert store.get_example_count(user_id, account_id) == 1
