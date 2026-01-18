"""Similarity-based transaction classifier using FAISS."""

import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

import faiss
import numpy as np
from numpy.typing import NDArray
from swen_ml_contracts import (
    AccountOption,
    ClassificationResult,
    ClassifyResponse,
    TransactionInput,
)

from ..storage.embedding_store import EmbeddingStore
from .encoder import TransactionEncoder

logger = logging.getLogger(__name__)


@dataclass
class AccountMatch:
    account_id: UUID
    account_number: str
    best_similarity: float
    match_type: Literal["example", "description"]
    matched_text: str | None = None


class SimilarityClassifier:
    """
    Classifies transactions by finding similar embeddings.

    Uses dual encoding: full text for example matching, keyword text for
    description matching. Example matches have priority over descriptions.
    """

    def __init__(
        self,
        encoder: TransactionEncoder,
        store: EmbeddingStore,
        similarity_threshold: float = 0.70,
        description_threshold: float = 0.45,
        max_examples_per_account: int = 100,
    ):
        self.encoder = encoder
        self.store = store
        self.threshold = similarity_threshold
        self.description_threshold = description_threshold
        self.max_examples = max_examples_per_account

    def classify(
        self,
        user_id: UUID,
        transaction: TransactionInput,
        available_accounts: list[AccountOption],
    ) -> ClassifyResponse:
        start_time = time.perf_counter()

        # Dual embeddings: full text for examples, keywords for descriptions
        full_text = self.encoder.build_text(
            purpose=transaction.purpose,
            amount=transaction.amount,
            counterparty_name=transaction.counterparty_name,
            reference=transaction.reference,
        )
        full_emb = self.encoder.encode(full_text)

        keyword_text = self.encoder.build_keyword_text(
            purpose=transaction.purpose,
            counterparty_name=transaction.counterparty_name,
        )
        keyword_emb = self.encoder.encode(keyword_text)

        # Load user's embeddings
        acc_embeddings = self.store.load_account_embeddings(user_id)
        txn_embeddings = self.store.load_transaction_embeddings(user_id)
        txn_texts = self.store.load_texts(user_id)

        # Find best match per account
        matches: list[AccountMatch] = []
        for acc in available_accounts:
            match = self._find_best_match(
                full_emb=full_emb,
                keyword_emb=keyword_emb,
                account=acc,
                acc_embedding=acc_embeddings.get(acc.account_id),
                txn_embeddings=txn_embeddings.get(acc.account_id),
                txn_texts=txn_texts.get(str(acc.account_id), []),
            )
            if match:
                matches.append(match)

        inference_time_ms = int((time.perf_counter() - start_time) * 1000)

        if not matches:
            return ClassifyResponse(
                account_id=None,
                account_number=None,
                similarity_score=0.0,
                confidence=0.0,
                margin_over_second=0.0,
                match_type=None,
                matched_text=None,
                reasoning="No matches found",
                inference_time_ms=inference_time_ms,
            )

        matches.sort(key=lambda m: m.best_similarity, reverse=True)
        best = matches[0]
        second = matches[1] if len(matches) > 1 else None

        confidence = self._compute_confidence(best, second)
        margin = best.best_similarity - (second.best_similarity if second else 0)

        # Lower threshold for cold-start (description-only matches)
        threshold = (
            self.threshold
            if best.match_type == "example"
            else self.description_threshold
        )
        return_account = confidence >= threshold

        return ClassifyResponse(
            account_id=best.account_id if return_account else None,
            account_number=best.account_number if return_account else None,
            similarity_score=best.best_similarity,
            confidence=confidence,
            margin_over_second=margin,
            match_type=best.match_type,
            matched_text=best.matched_text,
            reasoning=self._build_reasoning(best, second, confidence, return_account),
            inference_time_ms=inference_time_ms,
        )

    def classify_batch(
        self,
        user_id: UUID,
        transactions: list[TransactionInput],
        available_accounts: list[AccountOption],
    ) -> tuple[list[ClassificationResult], int]:
        start_time = time.perf_counter()

        acc_embeddings = self.store.load_account_embeddings(user_id)
        txn_embeddings = self.store.load_transaction_embeddings(user_id)
        txn_texts = self.store.load_texts(user_id)

        # Batch encode
        full_texts = [
            self.encoder.build_text(
                t.purpose, t.amount, t.counterparty_name, t.reference
            )
            for t in transactions
        ]
        keyword_texts = [
            self.encoder.build_keyword_text(t.purpose, t.counterparty_name)
            for t in transactions
        ]

        full_embeddings = self.encoder.encode_batch(full_texts)
        keyword_embeddings = self.encoder.encode_batch(keyword_texts)

        # Pre-build FAISS indices
        account_indices = self._build_account_indices(
            available_accounts, acc_embeddings, txn_embeddings
        )

        results = [
            self._classify_with_indices(
                full_emb, keyword_emb, available_accounts, account_indices, txn_texts
            )
            for full_emb, keyword_emb in zip(
                full_embeddings, keyword_embeddings, strict=True
            )
        ]

        total_time_ms = int((time.perf_counter() - start_time) * 1000)
        return results, total_time_ms

    def _find_best_match(
        self,
        full_emb: NDArray[np.float32],
        keyword_emb: NDArray[np.float32],
        account: AccountOption,
        acc_embedding: NDArray[np.float32] | None,
        txn_embeddings: NDArray[np.float32] | None,
        txn_texts: list[str],
    ) -> AccountMatch | None:
        best_similarity = 0.0
        match_type: Literal["example", "description"] = "description"
        matched_text: str | None = None

        # Check transaction examples (full embedding)
        if txn_embeddings is not None and txn_embeddings.shape[0] > 0:
            index = faiss.IndexFlatIP(txn_embeddings.shape[1])
            index.add(txn_embeddings.astype(np.float32))  # type: ignore[arg-type]
            similarities, indices = index.search(
                full_emb.reshape(1, -1).astype(np.float32), 1
            )  # type: ignore[arg-type]

            if similarities[0][0] > best_similarity:
                best_similarity = float(similarities[0][0])
                match_type = "example"
                if indices[0][0] < len(txn_texts):
                    matched_text = txn_texts[indices[0][0]]

        # Check account description (keyword embedding)
        if acc_embedding is not None:
            sim = float(np.dot(keyword_emb, acc_embedding))
            if sim > best_similarity:
                best_similarity = sim
                match_type = "description"
                matched_text = None

        if best_similarity <= 0:
            return None

        return AccountMatch(
            account_id=account.account_id,
            account_number=account.account_number,
            best_similarity=best_similarity,
            match_type=match_type,
            matched_text=matched_text,
        )

    def _build_account_indices(
        self,
        available_accounts: list[AccountOption],
        acc_embeddings: dict[UUID, NDArray[np.float32]],
        txn_embeddings: dict[UUID, NDArray[np.float32]],
    ) -> dict[UUID, tuple[faiss.IndexFlatIP | None, NDArray[np.float32] | None]]:
        indices = {}
        for acc in available_accounts:
            txn_emb = txn_embeddings.get(acc.account_id)
            if txn_emb is not None and txn_emb.shape[0] > 0:
                index = faiss.IndexFlatIP(txn_emb.shape[1])
                index.add(txn_emb.astype(np.float32))  # type: ignore[arg-type]
            else:
                index = None
            indices[acc.account_id] = (index, acc_embeddings.get(acc.account_id))
        return indices

    def _classify_with_indices(
        self,
        full_emb: NDArray[np.float32],
        keyword_emb: NDArray[np.float32],
        available_accounts: list[AccountOption],
        account_indices: dict[
            UUID, tuple[faiss.IndexFlatIP | None, NDArray[np.float32] | None]
        ],
        txn_texts: dict[str, list[str]],
    ) -> ClassificationResult:
        matches: list[AccountMatch] = []

        for acc in available_accounts:
            index, acc_emb = account_indices.get(acc.account_id, (None, None))

            best_similarity = 0.0
            match_type: Literal["example", "description"] = "description"
            matched_text: str | None = None

            if index is not None:
                similarities, indices = index.search(
                    full_emb.reshape(1, -1).astype(np.float32),
                    1,  # type: ignore[arg-type]
                )
                if similarities[0][0] > best_similarity:
                    best_similarity = float(similarities[0][0])
                    match_type = "example"
                    texts = txn_texts.get(str(acc.account_id), [])
                    if indices[0][0] < len(texts):
                        matched_text = texts[indices[0][0]]

            if acc_emb is not None:
                sim = float(np.dot(keyword_emb, acc_emb))
                if sim > best_similarity:
                    best_similarity = sim
                    match_type = "description"
                    matched_text = None

            if best_similarity > 0:
                matches.append(
                    AccountMatch(
                        account_id=acc.account_id,
                        account_number=acc.account_number,
                        best_similarity=best_similarity,
                        match_type=match_type,
                        matched_text=matched_text,
                    )
                )

        if not matches:
            return ClassificationResult(
                account_id=None,
                account_number=None,
                similarity_score=0.0,
                confidence=0.0,
                margin_over_second=0.0,
                match_type=None,
                matched_text=None,
                reasoning="No matches found",
            )

        matches.sort(key=lambda m: m.best_similarity, reverse=True)
        best = matches[0]
        second = matches[1] if len(matches) > 1 else None

        confidence = self._compute_confidence(best, second)
        margin = best.best_similarity - (second.best_similarity if second else 0)
        threshold = (
            self.threshold
            if best.match_type == "example"
            else self.description_threshold
        )
        return_account = confidence >= threshold

        return ClassificationResult(
            account_id=best.account_id if return_account else None,
            account_number=best.account_number if return_account else None,
            similarity_score=best.best_similarity,
            confidence=confidence,
            margin_over_second=margin,
            match_type=best.match_type,
            matched_text=best.matched_text,
            reasoning=self._build_reasoning(best, second, confidence, return_account),
        )

    def _compute_confidence(
        self, best: AccountMatch, second: AccountMatch | None
    ) -> float:
        margin = (
            best.best_similarity - second.best_similarity
            if second
            else best.best_similarity
        )
        margin_confidence = min(1.0, margin / 0.25)
        type_multiplier = 1.0 if best.match_type == "example" else 0.7
        bonus = (
            0.1 if best.match_type == "example" and best.best_similarity > 0.85 else 0.0
        )
        return min(1.0, (margin_confidence * type_multiplier) + bonus)

    def _build_reasoning(
        self,
        best: AccountMatch,
        second: AccountMatch | None,
        confidence: float,
        return_account: bool,
    ) -> str:
        if not return_account:
            if second:
                return (
                    f"Ambiguous: '{best.account_number}' ({best.best_similarity:.2f}) "
                    f"vs '{second.account_number}' ({second.best_similarity:.2f}). "
                    f"Confidence {confidence:.2f} below threshold."
                )
            return f"Low confidence ({confidence:.2f}) for '{best.account_number}'."

        if best.match_type == "example":
            preview = (
                best.matched_text[:50] + "..."
                if best.matched_text and len(best.matched_text) > 50
                else best.matched_text
            )
            return f"Matched '{preview}' (similarity: {best.best_similarity:.2f})"
        return f"Matched description for '{best.account_number}' (similarity: {best.best_similarity:.2f})"

    # Example management

    def add_example(
        self,
        user_id: UUID,
        account_id: UUID,
        purpose: str,
        amount: float,
        counterparty_name: str | None = None,
        reference: str | None = None,
        transaction_id: UUID | None = None,
    ) -> tuple[int, str, bool]:
        """Add example. Returns (total_count, text, was_added)."""
        if transaction_id and self.store.has_transaction_id(
            user_id, account_id, transaction_id
        ):
            text = self.encoder.build_text(
                purpose, Decimal(str(amount)), counterparty_name, reference
            )
            return self.store.get_example_count(user_id, account_id), text, False

        text = self.encoder.build_text(
            purpose, Decimal(str(amount)), counterparty_name, reference
        )
        embedding = self.encoder.encode(text)

        total = self.store.add_transaction_embedding(
            user_id, account_id, embedding, text, self.max_examples, transaction_id
        )
        self.store.update_metadata(
            user_id, self.encoder.model_name, self.encoder.embedding_dim
        )

        return total, text, True

    def embed_accounts(self, user_id: UUID, accounts: list[AccountOption]) -> int:
        embedded = 0
        for acc in accounts:
            text = f"{acc.name} | {acc.description}" if acc.description else acc.name
            embedding = self.encoder.encode(text)
            self.store.update_account_embedding(user_id, acc.account_id, embedding)
            embedded += 1

        if embedded:
            self.store.update_metadata(
                user_id, self.encoder.model_name, self.encoder.embedding_dim
            )
        return embedded

    def delete_account(self, user_id: UUID, account_id: UUID) -> int:
        return self.store.delete_account(user_id, account_id)

    def delete_user(self, user_id: UUID) -> tuple[int, int]:
        return self.store.delete_user(user_id)

    def get_user_stats(self, user_id: UUID) -> dict:
        acc_emb = self.store.load_account_embeddings(user_id)
        txn_emb = self.store.load_transaction_embeddings(user_id)
        examples_per_account = {str(k): v.shape[0] for k, v in txn_emb.items()}

        return {
            "total_examples": sum(examples_per_account.values()),
            "examples_per_account": examples_per_account,
            "accounts_with_examples": len(txn_emb),
            "accounts_without_examples": len(acc_emb) - len(txn_emb),
            "storage_bytes": self.store.get_storage_size(user_id),
        }
