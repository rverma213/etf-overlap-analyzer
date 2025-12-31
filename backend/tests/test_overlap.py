"""Tests for overlap calculation logic."""

import pytest
from app.overlap import calculate_overlap, OverlapResult, OverlappingHolding
from app.sec_parser import ETFHoldings, Holding


class TestCalculateOverlap:
    """Tests for the calculate_overlap function."""

    def test_identical_holdings(self) -> None:
        """Test overlap between two ETFs with identical holdings."""
        holdings1 = ETFHoldings(
            ticker="ETF1",
            name="Test ETF 1",
            holdings=[
                Holding(name="Apple Inc", cusip="037833100", percentage=10.0),
                Holding(name="Microsoft Corp", cusip="594918104", percentage=8.0),
            ],
        )
        holdings2 = ETFHoldings(
            ticker="ETF2",
            name="Test ETF 2",
            holdings=[
                Holding(name="Apple Inc", cusip="037833100", percentage=10.0),
                Holding(name="Microsoft Corp", cusip="594918104", percentage=8.0),
            ],
        )

        result = calculate_overlap(holdings1, holdings2)

        assert result.overlap_percentage == 18.0
        assert result.common_holdings_count == 2
        assert len(result.top_overlapping) == 2

    def test_no_overlap(self) -> None:
        """Test overlap between two ETFs with no common holdings."""
        holdings1 = ETFHoldings(
            ticker="ETF1",
            name="Test ETF 1",
            holdings=[
                Holding(name="Apple Inc", cusip="037833100", percentage=10.0),
            ],
        )
        holdings2 = ETFHoldings(
            ticker="ETF2",
            name="Test ETF 2",
            holdings=[
                Holding(name="Tesla Inc", cusip="88160R101", percentage=5.0),
            ],
        )

        result = calculate_overlap(holdings1, holdings2)

        assert result.overlap_percentage == 0.0
        assert result.common_holdings_count == 0
        assert len(result.top_overlapping) == 0

    def test_partial_overlap(self) -> None:
        """Test overlap uses minimum weight for common holdings."""
        holdings1 = ETFHoldings(
            ticker="ETF1",
            name="Test ETF 1",
            holdings=[
                Holding(name="Apple Inc", cusip="037833100", percentage=10.0),
                Holding(name="Microsoft Corp", cusip="594918104", percentage=8.0),
            ],
        )
        holdings2 = ETFHoldings(
            ticker="ETF2",
            name="Test ETF 2",
            holdings=[
                Holding(name="Apple Inc", cusip="037833100", percentage=5.0),  # Lower weight
                Holding(name="Tesla Inc", cusip="88160R101", percentage=7.0),
            ],
        )

        result = calculate_overlap(holdings1, holdings2)

        assert result.overlap_percentage == 5.0  # min(10, 5)
        assert result.common_holdings_count == 1

    def test_name_matching_fallback(self) -> None:
        """Test that name matching works when CUSIP is not available."""
        holdings1 = ETFHoldings(
            ticker="ETF1",
            name="Test ETF 1",
            holdings=[
                Holding(name="Apple Inc", cusip=None, percentage=10.0),
            ],
        )
        holdings2 = ETFHoldings(
            ticker="ETF2",
            name="Test ETF 2",
            holdings=[
                Holding(name="APPLE INC", cusip=None, percentage=8.0),  # Different case
            ],
        )

        result = calculate_overlap(holdings1, holdings2)

        assert result.overlap_percentage == 8.0
        assert result.common_holdings_count == 1

    def test_top_overlapping_limited_to_10(self) -> None:
        """Test that top overlapping is limited to 10 holdings."""
        holdings = [
            Holding(name=f"Stock {i}", cusip=f"CUSIP{i:03d}", percentage=1.0)
            for i in range(15)
        ]

        holdings1 = ETFHoldings(ticker="ETF1", name="Test ETF 1", holdings=holdings)
        holdings2 = ETFHoldings(ticker="ETF2", name="Test ETF 2", holdings=holdings)

        result = calculate_overlap(holdings1, holdings2)

        assert len(result.top_overlapping) == 10
        assert result.common_holdings_count == 15

    def test_result_structure(self) -> None:
        """Test that result contains all expected fields."""
        holdings1 = ETFHoldings(
            ticker="SPY",
            name="SPDR S&P 500",
            holdings=[Holding(name="Apple", cusip="037833100", percentage=7.0)],
        )
        holdings2 = ETFHoldings(
            ticker="QQQ",
            name="Invesco QQQ",
            holdings=[Holding(name="Apple", cusip="037833100", percentage=10.0)],
        )

        result = calculate_overlap(holdings1, holdings2)

        assert result.etf1_ticker == "SPY"
        assert result.etf2_ticker == "QQQ"
        assert result.etf1_name == "SPDR S&P 500"
        assert result.etf2_name == "Invesco QQQ"
        assert result.etf1_total_holdings == 1
        assert result.etf2_total_holdings == 1
        assert isinstance(result.top_overlapping[0], OverlappingHolding)

    def test_overlapping_holding_details(self) -> None:
        """Test that overlapping holding contains correct weights."""
        holdings1 = ETFHoldings(
            ticker="ETF1",
            name="Test ETF 1",
            holdings=[Holding(name="Apple", cusip="037833100", percentage=7.0)],
        )
        holdings2 = ETFHoldings(
            ticker="ETF2",
            name="Test ETF 2",
            holdings=[Holding(name="Apple", cusip="037833100", percentage=10.0)],
        )

        result = calculate_overlap(holdings1, holdings2)
        overlap = result.top_overlapping[0]

        assert overlap.name == "Apple"
        assert overlap.cusip == "037833100"
        assert overlap.weight_etf1 == 7.0
        assert overlap.weight_etf2 == 10.0
        assert overlap.overlap_contribution == 7.0
