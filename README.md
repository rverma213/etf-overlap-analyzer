# ETF Overlap Analyzer

A full-stack application to analyze holdings overlap between ETFs using SEC EDGAR N-PORT filings.

## Features

- Compare holdings between popular ETFs (SPY, QQQ, IVV, VOO, VTI)
- Visualize overlap percentage and common holdings
- Data sourced directly from SEC EDGAR N-PORT filings
- Automatic caching to minimize SEC API requests

## Project Structure

```
/backend
  /app
    main.py          # FastAPI application
    sec_parser.py    # SEC EDGAR N-PORT parser
    overlap.py       # Overlap calculation logic
  /tests             # Unit tests
  pyproject.toml     # Python dependencies
/frontend
  /src
    App.tsx          # Main React component
    api.ts           # API client
    types.ts         # TypeScript types
  package.json       # Node dependencies
docker-compose.yml   # Docker configuration
render.yaml          # Render deployment config
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- uv (Python package manager)

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:5173

### Docker

Run both services with Docker Compose:

```bash
docker-compose up --build
```

## API Endpoints

- `GET /api/etfs` - List available ETFs
- `GET /api/holdings/{ticker}` - Get holdings for an ETF
- `POST /api/overlap` - Analyze overlap between two ETFs
- `GET /health` - Health check

## Testing

```bash
cd backend
uv run pytest
```

## Deployment

This project includes a `render.yaml` for easy deployment to Render.

## Notes

- SEC EDGAR requires a User-Agent header and rate limiting (max 10 requests/sec)
- Holdings data is cached for 24 hours to reduce API calls
- Overlap percentage is calculated as the sum of minimum weights for common holdings
