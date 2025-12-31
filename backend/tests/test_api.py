"""Tests for FastAPI endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from app.main import app
from app.sec_parser import ETFHoldings, Holding


@pytest.fixture
def mock_holdings() -> ETFHoldings:
    """Create mock holdings for testing."""
    return ETFHoldings(
        ticker="SPY",
        name="SPDR S&P 500 ETF Trust",
        holdings=[
            Holding(name="Apple Inc", cusip="037833100", percentage=7.0, value=1000000),
            Holding(name="Microsoft Corp", cusip="594918104", percentage=6.5, value=950000),
            Holding(name="Amazon.com Inc", cusip="023135106", percentage=3.5, value=500000),
        ],
    )


class TestListETFs:
    """Tests for GET /api/etfs endpoint."""

    @pytest.mark.asyncio
    async def test_returns_available_etfs(self) -> None:
        """Test that endpoint returns list of available ETFs."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/etfs")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert all("ticker" in etf and "name" in etf for etf in data)

    @pytest.mark.asyncio
    async def test_contains_major_etfs(self) -> None:
        """Test that response includes major ETFs."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/etfs")

        tickers = [etf["ticker"] for etf in response.json()]
        assert "SPY" in tickers
        assert "QQQ" in tickers
        assert "VOO" in tickers


class TestGetHoldings:
    """Tests for GET /api/holdings/{ticker} endpoint."""

    @pytest.mark.asyncio
    async def test_invalid_ticker_returns_404(self) -> None:
        """Test that invalid ticker returns 404 error."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/holdings/INVALID")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_valid_ticker_returns_holdings(
        self, mock_holdings: ETFHoldings
    ) -> None:
        """Test that valid ticker returns holdings data."""
        with patch("app.main.get_etf_holdings", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_holdings

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/holdings/SPY")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "SPY"
        assert data["name"] == "SPDR S&P 500 ETF Trust"
        assert len(data["holdings"]) == 3

    @pytest.mark.asyncio
    async def test_sec_unavailable_returns_503(self) -> None:
        """Test that SEC data unavailability returns 503 error."""
        with patch("app.main.get_etf_holdings", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/holdings/SPY")

        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


class TestOverlapAnalysis:
    """Tests for POST /api/overlap endpoint."""

    @pytest.mark.asyncio
    async def test_invalid_ticker1_returns_404(self) -> None:
        """Test that invalid first ticker returns 404 error."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/overlap",
                json={"ticker1": "INVALID", "ticker2": "SPY"},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_ticker2_returns_404(self) -> None:
        """Test that invalid second ticker returns 404 error."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/overlap",
                json={"ticker1": "SPY", "ticker2": "INVALID"},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_same_ticker_returns_400(self) -> None:
        """Test that comparing same ticker returns 400 error."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/overlap",
                json={"ticker1": "SPY", "ticker2": "SPY"},
            )

        assert response.status_code == 400
        assert "different" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_valid_overlap_request(self) -> None:
        """Test successful overlap analysis."""
        holdings_spy = ETFHoldings(
            ticker="SPY",
            name="SPDR S&P 500 ETF Trust",
            holdings=[
                Holding(name="Apple Inc", cusip="037833100", percentage=7.0),
                Holding(name="Microsoft Corp", cusip="594918104", percentage=6.5),
            ],
        )
        holdings_qqq = ETFHoldings(
            ticker="QQQ",
            name="Invesco QQQ Trust",
            holdings=[
                Holding(name="Apple Inc", cusip="037833100", percentage=10.0),
                Holding(name="Microsoft Corp", cusip="594918104", percentage=9.0),
            ],
        )

        async def mock_get_holdings(ticker: str, **kwargs) -> ETFHoldings:
            return holdings_spy if ticker == "SPY" else holdings_qqq

        with patch("app.main.get_etf_holdings", side_effect=mock_get_holdings):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/overlap",
                    json={"ticker1": "SPY", "ticker2": "QQQ"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["etf1_ticker"] == "SPY"
        assert data["etf2_ticker"] == "QQQ"
        assert data["overlap_percentage"] == 13.5  # 7.0 + 6.5
        assert data["common_holdings_count"] == 2
        assert len(data["top_overlapping"]) == 2


class TestHealthCheck:
    """Tests for GET /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check endpoint returns healthy status."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
