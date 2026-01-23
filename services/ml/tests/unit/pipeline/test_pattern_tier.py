"""Tests for PatternTier."""

from decimal import Decimal
from uuid import uuid4

import pytest
from swen_ml.inference.pipeline import ClassificationContext, PatternTier
from swen_ml_contracts import AccountOption


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
        AccountOption(
            account_id=uuid4(),
            account_number="4200",
            name="Transport & Mobilität",
            account_type="expense",
            description="ÖPNV, Taxi, Benzin",
        ),
        AccountOption(
            account_id=uuid4(),
            account_number="4300",
            name="Restaurants & Bars",
            account_type="expense",
            description="Essen gehen",
        ),
        AccountOption(
            account_id=uuid4(),
            account_number="4400",
            name="Abonnements",
            account_type="expense",
            description="Streaming, Zeitschriften",
        ),
    ]


class TestPatternTier:
    def test_matches_rewe(self, accounts: list[AccountOption]) -> None:
        tier = PatternTier()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="REWE Berlin",
            amount=Decimal("-50.00"),
        )
        result = tier.classify("REWE Berlin", accounts, ctx)
        assert result is not None
        assert result.tier == "pattern"
        assert result.confidence == 1.0
        assert result.account_name == "Lebensmittel"
        assert "Supermarkt" in result.keywords

    def test_matches_spotify(self, accounts: list[AccountOption]) -> None:
        tier = PatternTier()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="SPOTIFY Stockholm",
            amount=Decimal("-9.99"),
        )
        result = tier.classify("SPOTIFY Stockholm", accounts, ctx)
        assert result is not None
        assert result.account_name == "Abonnements"
        assert "Streaming" in result.keywords

    def test_matches_energy_from_camelcase(self, accounts: list[AccountOption]) -> None:
        tier = PatternTier()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="NaturStromHandel GmbH Strom Abschlag",
            amount=Decimal("-120.00"),
        )
        result = tier.classify("NaturStromHandel GmbH Strom Abschlag", accounts, ctx)
        assert result is not None
        assert result.account_name is not None
        assert "Energie" in result.account_name or "Nebenkosten" in result.account_name
        assert "Strom" in result.keywords or "Energie" in result.keywords

    def test_matches_restaurant(self, accounts: list[AccountOption]) -> None:
        tier = PatternTier()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="Geile.Bar..Restaurant/Berlin",
            amount=Decimal("-35.00"),
        )
        result = tier.classify("Geile.Bar..Restaurant/Berlin", accounts, ctx)
        assert result is not None
        assert result.account_name is not None
        assert "Restaurant" in result.account_name or "Bar" in result.account_name

    def test_returns_none_for_unknown(self, accounts: list[AccountOption]) -> None:
        tier = PatternTier()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="UNKNOWN MERCHANT XYZ",
            amount=Decimal("-100.00"),
        )
        result = tier.classify("UNKNOWN MERCHANT XYZ", accounts, ctx)
        assert result is None

    def test_disabled_returns_none(self, accounts: list[AccountOption]) -> None:
        tier = PatternTier(enabled=False)
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="REWE Berlin",
            amount=Decimal("-50.00"),
        )
        result = tier.classify("REWE Berlin", accounts, ctx)
        assert result is None

    def test_empty_accounts_returns_none(self) -> None:
        tier = PatternTier()
        ctx = ClassificationContext(
            user_id=uuid4(),
            raw_text="REWE Berlin",
            amount=Decimal("-50.00"),
        )
        result = tier.classify("REWE Berlin", [], ctx)
        assert result is None
