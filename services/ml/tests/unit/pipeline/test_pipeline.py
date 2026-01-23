"""Tests for ClassificationPipeline."""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import numpy as np
import pytest
from swen_ml.config.settings import Settings
from swen_ml.inference.pipeline import ClassificationPipeline
from swen_ml_contracts import AccountOption


@pytest.fixture
def mock_encoder() -> MagicMock:
    """Create a mock TransactionEncoder."""
    encoder = MagicMock()
    encoder.build_text.return_value = "test text"
    encoder.encode.return_value = np.zeros(1024, dtype=np.float32)
    return encoder


@pytest.fixture
def mock_store() -> MagicMock:
    """Create a mock EmbeddingStore."""
    store = MagicMock()
    store.load_transaction_embeddings.return_value = {}
    store.load_texts.return_value = {}
    return store


@pytest.fixture
def mock_anchor_store() -> MagicMock:
    """Create a mock AnchorStore."""
    store = MagicMock()
    store.load_embeddings.return_value = {}
    store.load_texts.return_value = {}
    store.upsert_anchor.return_value = None
    store.delete_account.return_value = False
    store.delete_all_anchors.return_value = None
    return store


@pytest.fixture
def accounts() -> list[AccountOption]:
    return [
        AccountOption(
            account_id=uuid4(),
            account_number="4000",
            name="Lebensmittel",
            account_type="expense",
            description="Supermarkt und Einkäufe",
        ),
        AccountOption(
            account_id=uuid4(),
            account_number="4100",
            name="Energie & Nebenkosten",
            account_type="expense",
            description="Strom, Gas, Wasser",
        ),
    ]


class TestClassificationPipeline:
    def test_pattern_tier_matches_rewe(
        self,
        mock_encoder: MagicMock,
        mock_store: MagicMock,
        mock_anchor_store: MagicMock,
        accounts: list[AccountOption],
    ) -> None:
        settings = Settings(zero_shot_enabled=False)  # Don't load heavy model
        pipeline = ClassificationPipeline(mock_encoder, mock_store, mock_anchor_store, settings)

        result = pipeline.classify(
            user_id=uuid4(),
            raw_text="REWE Berlin Einkauf",
            amount=Decimal("-50.00"),
            accounts=accounts,
        )

        assert result is not None
        assert result.tier == "pattern"
        assert result.account_name == "Lebensmittel"
        assert result.confidence == 1.0

    def test_pattern_tier_matches_strom(
        self,
        mock_encoder: MagicMock,
        mock_store: MagicMock,
        mock_anchor_store: MagicMock,
        accounts: list[AccountOption],
    ) -> None:
        settings = Settings(zero_shot_enabled=False)
        pipeline = ClassificationPipeline(mock_encoder, mock_store, mock_anchor_store, settings)

        result = pipeline.classify(
            user_id=uuid4(),
            raw_text="Stadtwerke Strom Abschlag",
            amount=Decimal("-120.00"),
            accounts=accounts,
        )

        assert result is not None
        assert result.tier == "pattern"
        assert result.account_name is not None
        assert "Energie" in result.account_name or "Nebenkosten" in result.account_name

    def test_returns_none_for_unknown_transaction(
        self,
        mock_encoder: MagicMock,
        mock_store: MagicMock,
        mock_anchor_store: MagicMock,
        accounts: list[AccountOption],
    ) -> None:
        settings = Settings(zero_shot_enabled=False)
        pipeline = ClassificationPipeline(mock_encoder, mock_store, mock_anchor_store, settings)

        result = pipeline.classify(
            user_id=uuid4(),
            raw_text="UNKNOWN MERCHANT XYZ",
            amount=Decimal("-100.00"),
            accounts=accounts,
        )

        assert result is None

    def test_all_tiers_disabled_returns_none(
        self,
        mock_encoder: MagicMock,
        mock_store: MagicMock,
        mock_anchor_store: MagicMock,
        accounts: list[AccountOption],
    ) -> None:
        settings = Settings(
            pattern_enabled=False,
            embedding_enabled=False,
            zero_shot_enabled=False,
        )
        pipeline = ClassificationPipeline(mock_encoder, mock_store, mock_anchor_store, settings)

        result = pipeline.classify(
            user_id=uuid4(),
            raw_text="REWE Berlin",  # Would normally match pattern
            amount=Decimal("-50.00"),
            accounts=accounts,
        )

        assert result is None
