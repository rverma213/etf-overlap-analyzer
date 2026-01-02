"""FastAPI application for ETF Overlap Analyzer."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging

from .sec_parser import get_etf_holdings, get_available_etfs, ETF_INFO
from .overlap import calculate_overlap

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ETF Overlap Analyzer",
    description="Analyze holdings overlap between ETFs using SEC EDGAR data",
    version="1.0.0",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OverlapRequest(BaseModel):
    """Request body for overlap analysis."""

    ticker1: str
    ticker2: str


class HoldingResponse(BaseModel):
    """Response model for a single holding."""

    name: str
    cusip: str | None
    percentage: float
    value: float | None = None


class HoldingsResponse(BaseModel):
    """Response model for ETF holdings."""

    ticker: str
    name: str
    holdings: list[HoldingResponse]
    as_of_date: str | None = None


class OverlappingHoldingResponse(BaseModel):
    """Response model for an overlapping holding."""

    name: str
    cusip: str | None
    weight_etf1: float
    weight_etf2: float
    overlap_contribution: float


class OverlapResponse(BaseModel):
    """Response model for overlap analysis."""

    etf1_ticker: str
    etf2_ticker: str
    etf1_name: str
    etf2_name: str
    overlap_percentage: float
    common_holdings_count: int
    etf1_total_holdings: int
    etf2_total_holdings: int
    top_overlapping: list[OverlappingHoldingResponse]


class ETFInfo(BaseModel):
    """Response model for ETF info."""

    ticker: str
    name: str


@app.get("/api/etfs", response_model=list[ETFInfo])
async def list_etfs() -> list[ETFInfo]:
    """Get list of available ETFs.

    Returns:
        List of available ETF tickers and names.
    """
    return [ETFInfo(**etf) for etf in get_available_etfs()]


@app.get("/api/holdings/{ticker}", response_model=HoldingsResponse)
async def get_holdings(ticker: str) -> HoldingsResponse:
    """Get holdings for an ETF.

    Args:
        ticker: The ETF ticker symbol.

    Returns:
        Holdings data for the ETF.

    Raises:
        HTTPException: If ticker is not found or data cannot be fetched.
    """
    ticker = ticker.upper()

    if ticker not in ETF_INFO:
        raise HTTPException(
            status_code=404,
            detail=f"ETF '{ticker}' not found. Available ETFs: {list(ETF_INFO.keys())}",
        )

    holdings = await get_etf_holdings(ticker)

    if holdings is None:
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch holdings for '{ticker}'. SEC data may be unavailable.",
        )

    return HoldingsResponse(
        ticker=holdings.ticker,
        name=holdings.name,
        holdings=[
            HoldingResponse(
                name=h.name,
                cusip=h.cusip,
                percentage=h.percentage,
                value=h.value,
            )
            for h in holdings.holdings
        ],
        as_of_date=holdings.as_of_date,
    )


@app.post("/api/overlap", response_model=OverlapResponse)
async def analyze_overlap(request: OverlapRequest) -> OverlapResponse:
    """Analyze overlap between two ETFs.

    Args:
        request: The overlap request containing two ticker symbols.

    Returns:
        Overlap analysis results.

    Raises:
        HTTPException: If either ticker is not found or data cannot be fetched.
    """
    ticker1 = request.ticker1.upper()
    ticker2 = request.ticker2.upper()

    # Validate tickers
    for ticker in [ticker1, ticker2]:
        if ticker not in ETF_INFO:
            raise HTTPException(
                status_code=404,
                detail=f"ETF '{ticker}' not found. Available ETFs: {list(ETF_INFO.keys())}",
            )

    if ticker1 == ticker2:
        raise HTTPException(
            status_code=400,
            detail="Please select two different ETFs to compare.",
        )

    # Fetch holdings for both ETFs
    holdings1 = await get_etf_holdings(ticker1)
    holdings2 = await get_etf_holdings(ticker2)

    if holdings1 is None:
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch holdings for '{ticker1}'. SEC data may be unavailable.",
        )

    if holdings2 is None:
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch holdings for '{ticker2}'. SEC data may be unavailable.",
        )

    # Calculate overlap
    result = calculate_overlap(holdings1, holdings2)

    return OverlapResponse(
        etf1_ticker=result.etf1_ticker,
        etf2_ticker=result.etf2_ticker,
        etf1_name=result.etf1_name,
        etf2_name=result.etf2_name,
        overlap_percentage=result.overlap_percentage,
        common_holdings_count=result.common_holdings_count,
        etf1_total_holdings=result.etf1_total_holdings,
        etf2_total_holdings=result.etf2_total_holdings,
        top_overlapping=[
            OverlappingHoldingResponse(
                name=h.name,
                cusip=h.cusip,
                weight_etf1=h.weight_etf1,
                weight_etf2=h.weight_etf2,
                overlap_contribution=h.overlap_contribution,
            )
            for h in result.top_overlapping
        ],
    )


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status.
    """
    return {"status": "healthy"}
