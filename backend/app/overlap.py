"""ETF overlap calculation logic."""

from dataclasses import dataclass
from typing import Optional
from .sec_parser import ETFHoldings, Holding


@dataclass
class OverlappingHolding:
    """Represents a holding that appears in both ETFs."""

    name: str
    cusip: Optional[str]
    weight_etf1: float
    weight_etf2: float
    overlap_contribution: float


@dataclass
class OverlapResult:
    """Result of an overlap analysis between two ETFs."""

    etf1_ticker: str
    etf2_ticker: str
    etf1_name: str
    etf2_name: str
    overlap_percentage: float
    common_holdings_count: int
    etf1_total_holdings: int
    etf2_total_holdings: int
    top_overlapping: list[OverlappingHolding]


def calculate_overlap(holdings1: ETFHoldings, holdings2: ETFHoldings) -> OverlapResult:
    """Calculate the overlap between two ETFs.

    The overlap percentage is calculated as the sum of minimum weights
    for holdings that appear in both ETFs. For example, if ETF1 has
    3% in AAPL and ETF2 has 5% in AAPL, the overlap contribution is 3%.

    Args:
        holdings1: Holdings data for the first ETF.
        holdings2: Holdings data for the second ETF.

    Returns:
        OverlapResult with overlap metrics and top overlapping positions.
    """
    # Build lookup by CUSIP (more reliable than name matching)
    etf1_by_cusip: dict[str, Holding] = {}
    etf1_by_name: dict[str, Holding] = {}

    for h in holdings1.holdings:
        if h.cusip:
            etf1_by_cusip[h.cusip] = h
        etf1_by_name[h.name.upper()] = h

    overlapping: list[OverlappingHolding] = []
    total_overlap = 0.0

    for h2 in holdings2.holdings:
        # Try to match by CUSIP first, then by name
        h1 = None
        if h2.cusip and h2.cusip in etf1_by_cusip:
            h1 = etf1_by_cusip[h2.cusip]
        elif h2.name.upper() in etf1_by_name:
            h1 = etf1_by_name[h2.name.upper()]

        if h1:
            # Calculate overlap contribution (minimum of the two weights)
            overlap_contribution = min(h1.percentage, h2.percentage)
            total_overlap += overlap_contribution

            overlapping.append(OverlappingHolding(
                name=h1.name,
                cusip=h1.cusip,
                weight_etf1=h1.percentage,
                weight_etf2=h2.percentage,
                overlap_contribution=overlap_contribution,
            ))

    # Sort by overlap contribution descending
    overlapping.sort(key=lambda x: x.overlap_contribution, reverse=True)

    return OverlapResult(
        etf1_ticker=holdings1.ticker,
        etf2_ticker=holdings2.ticker,
        etf1_name=holdings1.name,
        etf2_name=holdings2.name,
        overlap_percentage=round(total_overlap, 2),
        common_holdings_count=len(overlapping),
        etf1_total_holdings=len(holdings1.holdings),
        etf2_total_holdings=len(holdings2.holdings),
        top_overlapping=overlapping[:10],  # Top 10 overlapping positions
    )
