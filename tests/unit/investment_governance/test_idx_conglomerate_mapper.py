"""Unit tests for IDX Conglomerate Mapper -- Sprint-59.

Validates that every ticker defined in MANDATE.md's Conglomerate Exposure
section maps to the correct group and limit.
"""

import pytest

from karsa.investment_governance.domain.value_objects.idx_conglomerate_mapper import (
    CONGLOMERATE_GROUPS,
    CONGLOMERATE_LIMITS,
    CONGLOMERATE_MAP,
    get_conglomerate_group,
    get_conglomerate_limit,
    get_group_tickers,
    is_conglomerate_ticker,
)


# --- MANDATE.md ticker-to-group mapping ---

class TestConglomerateMapCoverage:
    """Every MANDATE.md ticker must be present in the map."""

    @pytest.mark.parametrize("ticker, expected_group", [
        ("BBCA", "Djarum/BCA"),
        ("BGTN", "Djarum/BCA"),
        ("ASII", "Astra"),
        ("AUTO", "Astra"),
        ("SMSM", "Astra"),
        ("BMRI", "Sinar Mas"),
        ("SMGR", "Sinar Mas"),
        ("Djarum", "Sinar Mas"),
        ("ICBP", "Salim"),
        ("INDF", "Salim"),
        ("LPKR", "Lippo"),
        ("LPPF", "Lippo"),
        ("MEDC", "Prajogo"),
        ("MBSS", "Prajogo"),
        ("BKSL", "Bakrie"),
        ("BIPI", "Bakrie"),
        ("ANTM", "Bakrie"),
    ])
    def test_ticker_maps_to_correct_group(self, ticker: str, expected_group: str):
        assert get_conglomerate_group(ticker) == expected_group

    @pytest.mark.parametrize("ticker, expected_group", [
        ("BBCA", "Djarum/BCA"),
        ("BGTN", "Djarum/BCA"),
        ("ASII", "Astra"),
        ("AUTO", "Astra"),
        ("SMSM", "Astra"),
        ("BMRI", "Sinar Mas"),
        ("SMGR", "Sinar Mas"),
        ("Djarum", "Sinar Mas"),
        ("ICBP", "Salim"),
        ("INDF", "Salim"),
        ("LPKR", "Lippo"),
        ("LPPF", "Lippo"),
        ("MEDC", "Prajogo"),
        ("MBSS", "Prajogo"),
        ("BKSL", "Bakrie"),
        ("BIPI", "Bakrie"),
        ("ANTM", "Bakrie"),
    ])
    def test_ticker_in_conglomerate_map(self, ticker: str, expected_group: str):
        assert ticker.upper() in CONGLOMERATE_MAP
        assert CONGLOMERATE_MAP[ticker.upper()][0] == expected_group


# --- Limit values from MANDATE.md ---

class TestConglomerateLimits:
    """Limits must match MANDATE.md values exactly."""

    @pytest.mark.parametrize("group, expected_limit", [
        ("Djarum/BCA", 0.15),
        ("Astra", 0.12),
        ("Sinar Mas", 0.10),
        ("Salim", 0.08),
        ("Lippo", 0.05),
        ("Prajogo", 0.08),
        ("Bakrie", 0.05),
    ])
    def test_group_limits(self, group: str, expected_limit: float):
        assert CONGLOMERATE_LIMITS[group] == expected_limit

    @pytest.mark.parametrize("ticker, expected_limit", [
        ("BBCA", 0.15),
        ("ASII", 0.12),
        ("BMRI", 0.10),
        ("ICBP", 0.08),
        ("LPKR", 0.05),
        ("MEDC", 0.08),
        ("BKSL", 0.05),
    ])
    def test_ticker_limit(self, ticker: str, expected_limit: float):
        assert get_conglomerate_limit(ticker) == expected_limit


# --- Case insensitivity ---

class TestCaseInsensitivity:
    """Ticker lookups must be case-insensitive."""

    @pytest.mark.parametrize("ticker", ["bbca", "Bbca", "BBCA", "bbCa"])
    def test_case_insensitive_group_lookup(self, ticker: str):
        assert get_conglomerate_group(ticker) == "Djarum/BCA"

    @pytest.mark.parametrize("ticker", ["asii", "asII", "ASII"])
    def test_case_insensitive_limit_lookup(self, ticker: str):
        assert get_conglomerate_limit(ticker) == 0.12

    @pytest.mark.parametrize("ticker", ["bbca", "BBCA"])
    def test_is_conglomerate_ticker_case_insensitive(self, ticker: str):
        assert is_conglomerate_ticker(ticker) is True


# --- Unknown tickers ---

class TestUnknownTickers:
    """Non-conglomerate tickers must return None / False."""

    @pytest.mark.parametrize("ticker", ["TLKM", "BBCA ", " GOOG", "", "XYZZ"])
    def test_unknown_returns_none_group(self, ticker: str):
        assert get_conglomerate_group(ticker) is None

    @pytest.mark.parametrize("ticker", ["TLKM", "BBCA ", "XYZZ"])
    def test_unknown_returns_none_limit(self, ticker: str):
        assert get_conglomerate_limit(ticker) is None

    @pytest.mark.parametrize("ticker", ["TLKM", "XYZZ", "GOOG"])
    def test_unknown_not_conglomerate_ticker(self, ticker: str):
        assert is_conglomerate_ticker(ticker) is False


# --- Group tickers retrieval ---

class TestGetGroupTickers:

    def test_returns_tickers_for_known_group(self):
        tickers = get_group_tickers("Astra")
        assert tickers == ["ASII", "AUTO", "SMSM"]

    def test_returns_empty_for_unknown_group(self):
        assert get_group_tickers("NonExistent") == []

    def test_all_groups_retrievable(self):
        for group_name, expected_tickers, _ in CONGLOMERATE_GROUPS:
            assert get_group_tickers(group_name) == expected_tickers


# --- Structural integrity ---

class TestStructuralIntegrity:

    def test_seven_conglomerate_groups(self):
        """MANDATE.md defines exactly 7 conglomerate groups."""
        assert len(CONGLOMERATE_GROUPS) == 7

    def test_total_mapped_tickers(self):
        """MANDATE.md defines 17 tickers across all groups."""
        assert len(CONGLOMERATE_MAP) == 17

    def test_no_duplicate_tickers_across_groups(self):
        """A ticker must belong to exactly one group."""
        all_tickers = []
        for _, tickers, _ in CONGLOMERATE_GROUPS:
            all_tickers.extend(tickers)
        assert len(all_tickers) == len(set(all_tickers))

    def test_conglomerate_map_matches_groups(self):
        """CONGLOMERATE_MAP must be consistent with CONGLOMERATE_GROUPS."""
        for group_name, tickers, limit in CONGLOMERATE_GROUPS:
            for ticker in tickers:
                assert CONGLOMERATE_MAP[ticker.upper()] == (group_name, limit)
