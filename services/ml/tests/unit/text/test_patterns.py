"""Tests for pattern keywords."""

import re

import pytest
from swen_ml.text.patterns import PATTERN_KEYWORDS


class TestPatternKeywords:
    def test_patterns_are_valid_regex(self) -> None:
        for pattern in PATTERN_KEYWORDS:
            # Should not raise
            re.compile(pattern, re.IGNORECASE)

    def test_keywords_are_non_empty(self) -> None:
        for pattern, keywords in PATTERN_KEYWORDS.items():
            assert len(keywords) > 0, f"Pattern {pattern} has no keywords"

    def test_supermarket_patterns_exist(self) -> None:
        assert r"\brewe\b" in PATTERN_KEYWORDS

    def test_energy_patterns_exist(self) -> None:
        strom_patterns = [p for p in PATTERN_KEYWORDS if "strom" in p]
        assert len(strom_patterns) >= 1


class TestPatternMatching:
    @pytest.mark.parametrize(
        "text,expected_pattern",
        [
            ("rewe berlin", r"\brewe\b"),
            ("REWE BERLIN", r"\brewe\b"),
            ("spotify stockholm", r"\bspotify\b"),
            ("naturstrom handel strom", r"\bstrom\b"),
            ("stadtwerke berlin gas abschlag", r"\bgas\b(?!tr)"),
        ],
    )
    def test_patterns_match_expected_text(
        self, text: str, expected_pattern: str
    ) -> None:
        pattern = re.compile(expected_pattern, re.IGNORECASE)
        assert pattern.search(text) is not None

    def test_gas_pattern_excludes_gastronomie(self) -> None:
        pattern = re.compile(r"\bgas\b(?!tr)", re.IGNORECASE)
        assert pattern.search("gastronomie") is None
        assert pattern.search("gas abschlag") is not None
