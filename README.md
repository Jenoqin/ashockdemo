# A-Share ETF Quant Research

A web application designed for A-Share ETF and Equity quantitative research, integrating market data, technical analysis, asset profiling, and backtesting.

## Features

- **Market Data Visualization:** Responsive ECharts with price candlesticks, volume bars, and configurable technical overlays (MA, BOLL, MACD, RSI).
- **Technical Analysis:** Calculates annualized returns, volatility, Sharpe, Sortino, max drawdown, and proprietary diagnostic scores across Trend, Momentum, Volatility, and Drawdown dimensions.
- **Asset Profiles:** Detailed views for ETFs (tracking index, size, top holdings) and Equities (industry, valuation, financial periods).
- **Strategy Lab:** Dual Moving Average crossover backtesting lab with configurable fast/slow windows, fee rate, and slippage. Provides trade logs and equity curves.

## Tech Stack

**Backend:**
- Python 3.12, FastAPI, Pydantic v2
- Pandas, NumPy, TA-Lib (via ta package)
- AkShare, Tushare (optional) for market data
- SQLite for local caching

**Frontend:**
- React 18, TypeScript, Vite
- ECharts (echarts for react)
- CSS variables/tokens based styling

## Quick Start

### 1. Prerequisites
- Node.js 18+
- Python 3.12+ (uv or standard venv)

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
# Edit .env with your Tushare token if you have one
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

### 4. Run Application
Run the full stack via Makefile:
```bash
make run
```
Then navigate to `http://127.0.0.1:5173`.

## Testing

```bash
# Run backend and frontend unit tests
make test

# Run E2E tests (Playwright)
make test-e2e

# Run Live Smoke Test (Verifies external data sources)
make smoke-live
```
