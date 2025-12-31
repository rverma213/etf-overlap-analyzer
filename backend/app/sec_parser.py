"""SEC EDGAR N-PORT filing parser for ETF holdings data."""

import asyncio
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional
import aiohttp
import logging
from pathlib import Path
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# SEC requires a User-Agent header with contact info
SEC_USER_AGENT = "ETF-Overlap-Analyzer/1.0 (contact@example.com)"

# Cache directory for SEC responses
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_EXPIRY_HOURS = 24

# ETF ticker to SEC filing info mapping
# Each entry contains: CIK (for the fund series), series_id (to identify specific fund in filing)
ETF_INFO = {
    "SPY": {
        "name": "SPDR S&P 500 ETF Trust",
        "cik": "0000884394",
        "series_id": None,  # Single fund filing
    },
    "QQQ": {
        "name": "Invesco QQQ Trust",
        "cik": "0001067839",
        "series_id": None,
    },
    "IVV": {
        "name": "iShares Core S&P 500 ETF",
        "cik": "0000893818",
        "series_id": "S000000104",
    },
    "VOO": {
        "name": "Vanguard S&P 500 ETF",
        "cik": "0000102909",
        "series_id": "S000584",
    },
    "VTI": {
        "name": "Vanguard Total Stock Market ETF",
        "cik": "0000102909",
        "series_id": "S000002845",
    },
}


@dataclass
class Holding:
    """Represents a single ETF holding."""

    name: str
    cusip: Optional[str]
    percentage: float
    value: Optional[float] = None


@dataclass
class ETFHoldings:
    """Represents all holdings for an ETF."""

    ticker: str
    name: str
    holdings: list[Holding]
    as_of_date: Optional[str] = None


def _get_cache_path(ticker: str) -> Path:
    """Get the cache file path for an ETF ticker.

    Args:
        ticker: The ETF ticker symbol.

    Returns:
        Path to the cache file.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{ticker.upper()}_holdings.json"


def _is_cache_valid(cache_path: Path) -> bool:
    """Check if a cache file exists and is not expired.

    Args:
        cache_path: Path to the cache file.

    Returns:
        True if cache is valid and not expired.
    """
    if not cache_path.exists():
        return False

    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
    return datetime.now() - mtime < timedelta(hours=CACHE_EXPIRY_HOURS)


def _load_from_cache(ticker: str) -> Optional[ETFHoldings]:
    """Load holdings from cache if available and not expired.

    Args:
        ticker: The ETF ticker symbol.

    Returns:
        ETFHoldings if cache hit, None otherwise.
    """
    cache_path = _get_cache_path(ticker)
    if not _is_cache_valid(cache_path):
        return None

    try:
        with open(cache_path, "r") as f:
            data = json.load(f)
        holdings = [Holding(**h) for h in data["holdings"]]
        return ETFHoldings(
            ticker=data["ticker"],
            name=data["name"],
            holdings=holdings,
            as_of_date=data.get("as_of_date"),
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to load cache for {ticker}: {e}")
        return None


def _save_to_cache(holdings: ETFHoldings) -> None:
    """Save holdings to cache.

    Args:
        holdings: The ETF holdings to cache.
    """
    cache_path = _get_cache_path(holdings.ticker)
    data = {
        "ticker": holdings.ticker,
        "name": holdings.name,
        "holdings": [
            {
                "name": h.name,
                "cusip": h.cusip,
                "percentage": h.percentage,
                "value": h.value,
            }
            for h in holdings.holdings
        ],
        "as_of_date": holdings.as_of_date,
    }
    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)


async def _fetch_with_rate_limit(
    session: aiohttp.ClientSession, url: str, delay: float = 0.1
) -> str:
    """Fetch URL with rate limiting for SEC compliance.

    Args:
        session: The aiohttp session.
        url: URL to fetch.
        delay: Delay in seconds between requests.

    Returns:
        Response text.

    Raises:
        aiohttp.ClientError: If the request fails.
    """
    await asyncio.sleep(delay)  # Rate limiting
    headers = {"User-Agent": SEC_USER_AGENT}
    async with session.get(url, headers=headers) as response:
        response.raise_for_status()
        return await response.text()


async def _get_latest_nport_url(session: aiohttp.ClientSession, cik: str) -> Optional[str]:
    """Get the URL of the latest N-PORT filing for a CIK.

    Args:
        session: The aiohttp session.
        cik: The SEC CIK number.

    Returns:
        URL to the N-PORT XML filing, or None if not found.
    """
    # Use SEC EDGAR API to get filings
    cik_padded = cik.lstrip("0").zfill(10)
    submissions_url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"

    try:
        text = await _fetch_with_rate_limit(session, submissions_url)
        data = json.loads(text)

        # Find most recent N-PORT filing
        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accession_numbers = filings.get("accessionNumber", [])

        for i, form in enumerate(forms):
            if form in ("NPORT-P", "NPORT-P/A"):
                accession = accession_numbers[i]
                accession_no_dash = accession.replace("-", "")

                # Get the filing index to find the XML file
                index_url = f"https://www.sec.gov/Archives/edgar/data/{cik_padded}/{accession_no_dash}/index.json"
                index_text = await _fetch_with_rate_limit(session, index_url)
                index_data = json.loads(index_text)

                # Look for the primary XML file (usually ends with .xml and contains nport)
                for item in index_data.get("directory", {}).get("item", []):
                    name = item.get("name", "")
                    if name.endswith(".xml") and "nport" in name.lower():
                        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_padded}/{accession_no_dash}/{name}"
                        logger.info(f"Found N-PORT XML file: {name}")
                        return filing_url

                # Fallback: look for any XML file that's not the primary document
                for item in index_data.get("directory", {}).get("item", []):
                    name = item.get("name", "")
                    if name.endswith(".xml"):
                        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_padded}/{accession_no_dash}/{name}"
                        logger.info(f"Found XML file: {name}")
                        return filing_url

        logger.warning(f"No N-PORT filing found for CIK {cik}")
        return None

    except Exception as e:
        logger.error(f"Error fetching filings for CIK {cik}: {e}")
        return None


def _parse_nport_xml(xml_content: str, series_id: Optional[str] = None) -> list[Holding]:
    """Parse N-PORT XML content to extract holdings.

    Args:
        xml_content: The XML content of the N-PORT filing.
        series_id: Optional series ID to filter for specific fund.

    Returns:
        List of holdings extracted from the filing.
    """
    holdings = []

    # Try to extract namespace from the XML content
    ns_match = re.search(r'xmlns="([^"]+)"', xml_content)
    default_ns = ns_match.group(1) if ns_match else ""

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.error(f"Failed to parse XML: {e}")
        # Try to clean the XML and parse again
        try:
            # Remove any BOM or leading whitespace
            cleaned = xml_content.strip()
            if cleaned.startswith('\ufeff'):
                cleaned = cleaned[1:]
            root = ET.fromstring(cleaned)
        except ET.ParseError as e2:
            logger.error(f"Failed to parse cleaned XML: {e2}")
            return holdings

    # Build namespace dict dynamically
    namespaces = {}
    if default_ns:
        namespaces["ns"] = default_ns

    # Try multiple approaches to find investment/security elements
    invstOrSecs = []

    # Approach 1: Try with detected namespace
    if namespaces:
        invstOrSecs = root.findall(".//{%s}invstOrSec" % default_ns)

    # Approach 2: Try common SEC namespaces
    if not invstOrSecs:
        for ns_uri in [
            "http://www.sec.gov/edgar/nport",
            "http://www.sec.gov/edgar/nportfiling",
            "http://www.sec.gov/edgar/document/nport",
        ]:
            invstOrSecs = root.findall(".//{%s}invstOrSec" % ns_uri)
            if invstOrSecs:
                default_ns = ns_uri
                break

    # Approach 3: Try without namespace using local-name()
    if not invstOrSecs:
        # Use iter to find elements by local name
        invstOrSecs = [elem for elem in root.iter() if elem.tag.endswith("}invstOrSec") or elem.tag == "invstOrSec"]

    logger.info(f"Found {len(invstOrSecs)} investment/security elements")

    for inv in invstOrSecs:
        try:
            # Helper function to find element by local name
            def find_elem(parent: ET.Element, local_name: str) -> Optional[ET.Element]:
                # Try with namespace
                if default_ns:
                    elem = parent.find("{%s}%s" % (default_ns, local_name))
                    if elem is not None:
                        return elem
                # Try without namespace
                elem = parent.find(local_name)
                if elem is not None:
                    return elem
                # Try iterating children
                for child in parent:
                    if child.tag.endswith("}" + local_name) or child.tag == local_name:
                        return child
                return None

            # Extract name
            name_elem = find_elem(inv, "name")
            name = name_elem.text.strip() if name_elem is not None and name_elem.text else "Unknown"

            # Extract CUSIP
            cusip_elem = find_elem(inv, "cusip")
            cusip = cusip_elem.text.strip() if cusip_elem is not None and cusip_elem.text else None

            # Extract percentage of net assets
            pct_elem = find_elem(inv, "pctVal")
            percentage = float(pct_elem.text) if pct_elem is not None and pct_elem.text else 0.0

            # Extract value
            val_elem = find_elem(inv, "valUSD")
            value = float(val_elem.text) if val_elem is not None and val_elem.text else None

            if percentage > 0:  # Only include holdings with positive weight
                holdings.append(Holding(
                    name=name,
                    cusip=cusip,
                    percentage=percentage,
                    value=value,
                ))
        except (AttributeError, ValueError) as e:
            logger.debug(f"Error parsing holding: {e}")
            continue

    # Sort by percentage descending
    holdings.sort(key=lambda h: h.percentage, reverse=True)

    return holdings


async def get_etf_holdings(ticker: str, force_refresh: bool = False) -> Optional[ETFHoldings]:
    """Get holdings for an ETF by ticker.

    Args:
        ticker: The ETF ticker symbol (e.g., 'SPY', 'QQQ').
        force_refresh: If True, bypass cache and fetch fresh data.

    Returns:
        ETFHoldings object with the holdings data, or None if not found.
    """
    ticker = ticker.upper()

    if ticker not in ETF_INFO:
        logger.error(f"Unknown ETF ticker: {ticker}")
        return None

    # Check cache first
    if not force_refresh:
        cached = _load_from_cache(ticker)
        if cached:
            logger.info(f"Loaded {ticker} holdings from cache")
            return cached

    etf_info = ETF_INFO[ticker]

    async with aiohttp.ClientSession() as session:
        # Get latest N-PORT filing URL
        filing_url = await _get_latest_nport_url(session, etf_info["cik"])
        if not filing_url:
            return None

        logger.info(f"Fetching N-PORT filing from: {filing_url}")

        try:
            xml_content = await _fetch_with_rate_limit(session, filing_url)
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch N-PORT filing: {e}")
            return None

        # Parse the XML
        holdings = _parse_nport_xml(xml_content, etf_info.get("series_id"))

        if not holdings:
            logger.warning(f"No holdings found in N-PORT filing for {ticker}")
            return None

        result = ETFHoldings(
            ticker=ticker,
            name=etf_info["name"],
            holdings=holdings,
        )

        # Save to cache
        _save_to_cache(result)

        return result


def get_available_etfs() -> list[dict]:
    """Get list of available ETFs.

    Returns:
        List of ETF info dictionaries with ticker and name.
    """
    return [
        {"ticker": ticker, "name": info["name"]}
        for ticker, info in ETF_INFO.items()
    ]
