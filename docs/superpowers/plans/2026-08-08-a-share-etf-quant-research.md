# A 股 / ETF 量化研究台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个本地一键启动、默认研究 512480.SH、同时支持普通 A 股与场内 ETF 的现代化量化研究 Web 原型。

**Architecture:** React/TypeScript/Vite 前端通过 REST API 调用 FastAPI 后端；后端以统一 Provider 协议接入 AkShare 和 Tushare，以 SQLite 缓存标准化数据，并把指标计算与回测保持为无网络依赖的纯服务。资产类型决定展示 ETF 特征或公司基本面，但行情、风险分析和回测共用同一条数据链路。

**Tech Stack:** Python 3.11+、FastAPI、Pydantic、Pandas、NumPy、AkShare、Tushare、SQLite、pytest；Node.js 20+、React、TypeScript、Vite、ECharts、Vitest、Testing Library、Playwright。

## Global Constraints

- 默认标的是 `512480.SH`，但不得在数据服务或分析函数中写死该代码。
- AkShare 是默认主源；配置 `TUSHARE_TOKEN` 后启用 Tushare 备用源和最近 20 个交易日交叉校验。
- Token 只允许从后端环境变量读取，前端资源、API 响应和日志中不得出现 Token。
- 所有真实数据响应必须包含来源、抓取时间、缓存状态、演示数据标志和质量告警。
- 演示数据必须设置 `is_demo=true` 并在页面显著标识，不能冒充真实行情。
- 核心金融计算只在后端执行；前端只负责输入、状态管理和展示。
- 回测信号在收盘后形成，并在下一交易日开盘执行；计入手续费与滑点，禁止未来函数。
- 页面固定展示“仅供个人研究学习，不构成投资建议”。
- 视觉采用“研究手记”：暖白 `#F5F1E8`、纸白 `#FFFDF7`、墨色 `#24231F`、砖红 `#D55331`、灰线 `#D9D2C4`。
- 自动化测试默认不访问外部网络；真实数据只通过单独的 smoke 命令验证。

## File Structure

```text
.
├── Makefile                         # 一键安装、启动、测试和真实数据 smoke
├── README.md                        # 本地运行、Token、数据口径与免责声明
├── .env.example                     # 无秘密的配置模板
├── backend/
│   ├── pyproject.toml               # Python 包与测试配置
│   ├── src/quantlab/
│   │   ├── main.py                  # FastAPI 应用工厂与中间件
│   │   ├── config.py                # 环境配置
│   │   ├── errors.py                # 稳定业务错误码
│   │   ├── models.py                # 跨层领域与 API 模型
│   │   ├── cache.py                 # SQLite 行情与同步区间仓储
│   │   ├── providers/
│   │   │   ├── base.py              # Provider 协议与代码规范化
│   │   │   ├── akshare_provider.py  # AkShare 适配器
│   │   │   ├── tushare_provider.py  # Tushare 适配器
│   │   │   └── demo_provider.py     # 仅显式演示模式使用的确定性数据
│   │   ├── services/
│   │   │   ├── market_data.py       # 缓存、降级、交叉校验编排
│   │   │   ├── quality.py           # OHLCV 数据质量检查
│   │   │   ├── analytics.py         # 技术、收益、风险与透明评分
│   │   │   ├── assets.py            # ETF/普通股票资料编排
│   │   │   └── backtest.py          # 双均线事件回测
│   │   └── api/
│   │       ├── dependencies.py      # 服务依赖组装
│   │       ├── instruments.py       # 搜索与资产资料路由
│   │       ├── market.py            # 行情、分析与刷新路由
│   │       └── backtests.py         # 回测路由
│   └── tests/
│       ├── test_cache.py
│       ├── test_providers.py
│       ├── test_market_data.py
│       ├── test_quality.py
│       ├── test_analytics.py
│       ├── test_assets.py
│       ├── test_backtest.py
│       └── test_api.py
├── frontend/
│   ├── package.json                 # Web 依赖与脚本
│   ├── vite.config.ts               # Vite 与本地 API 代理
│   ├── src/
│   │   ├── main.tsx                 # React 入口
│   │   ├── App.tsx                  # 页面状态与区域组合
│   │   ├── api/client.ts            # 类型安全的 REST 客户端
│   │   ├── api/types.ts             # 与 Pydantic 契约对应的 TS 类型
│   │   ├── hooks/useResearch.ts     # 标的、区间、刷新与错误状态
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── InstrumentHero.tsx
│   │   │   ├── MarketChart.tsx
│   │   │   ├── MetricGrid.tsx
│   │   │   ├── AssetProfile.tsx
│   │   │   ├── BacktestLab.tsx
│   │   │   ├── DataProvenance.tsx
│   │   │   └── StatePanel.tsx
│   │   └── styles/
│   │       ├── tokens.css
│   │       └── app.css
│   └── src/__tests__/
│       ├── fixtures.ts
│       ├── App.test.tsx
│       ├── MarketChart.test.tsx
│       └── BacktestLab.test.tsx
└── scripts/
    └── smoke_live_data.py           # 真实 512480 数据链路检查
```

---

### Task 1: 可运行的前后端工程骨架

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/quantlab/__init__.py`
- Create: `backend/src/quantlab/config.py`
- Create: `backend/src/quantlab/main.py`
- Create: `backend/tests/test_health.py`
- Create: `frontend/` via Vite React TypeScript scaffold
- Modify: `frontend/package.json`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/__tests__/App.test.tsx`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: none.
- Produces: `create_app() -> FastAPI`, `GET /api/health`, a React app rendering `量研手记`.

- [ ] **Step 1: Scaffold the backend package and frontend application**

Run:

```bash
mkdir -p backend/src/quantlab backend/tests
npm create vite@latest frontend -- --template react-ts
```

Execute both commands from `/home/ubuntu/vibe-coding`. Create `backend/pyproject.toml` with these exact dependency groups:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "quantlab-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "akshare",
  "fastapi",
  "numpy",
  "pandas",
  "pydantic-settings",
  "tushare",
  "uvicorn[standard]",
]

[project.optional-dependencies]
dev = ["httpx", "pytest", "pytest-cov"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.setuptools.packages.find]
where = ["src"]
```

Then run:

```bash
cd frontend
npm install echarts
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 2: Write failing health and shell tests**

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient
from quantlab.main import create_app

def test_health_reports_service_status():
    response = TestClient(create_app()).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "quantlab-api",
        "primary_provider": "akshare",
        "fallback_enabled": False,
    }
```

```tsx
// frontend/src/__tests__/App.test.tsx
import '@testing-library/jest-dom/vitest'
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from '../App'

describe('App', () => {
  it('renders the research product identity and disclaimer', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: '量研手记' })).toBeInTheDocument()
    expect(screen.getByText('仅供个人研究学习，不构成投资建议')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: Run both tests and verify RED**

Run:

```bash
cd backend
python -m pytest tests/test_health.py -v
cd ../frontend
npm test -- --run src/__tests__/App.test.tsx
```

Expected: backend fails because `quantlab.main` is absent; frontend fails because the scaffold does not render the required text.

- [ ] **Step 4: Implement the minimum application factories**

```python
# backend/src/quantlab/config.py
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    tushare_token: str | None = Field(default=None, validation_alias="TUSHARE_TOKEN")
    database_path: str = Field(default="./data/quantlab.db", validation_alias="QUANTLAB_DATABASE_PATH")
    demo_mode: bool = Field(default=False, validation_alias="QUANTLAB_DEMO_MODE")
    frontend_origin: str = Field(default="http://localhost:5173", validation_alias="QUANTLAB_FRONTEND_ORIGIN")
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# backend/src/quantlab/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="QuantLab API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "service": "quantlab-api",
            "primary_provider": "akshare",
            "fallback_enabled": bool(settings.tushare_token),
        }

    return app

app = create_app()
```

Replace `frontend/src/App.tsx` with a minimal semantic shell containing an `h1` with `量研手记` and a footer with the exact disclaimer. Add `"test": "vitest"` to `frontend/package.json` scripts and configure jsdom in `vite.config.ts`.

- [ ] **Step 5: Run tests and verify GREEN**

Run the two commands from Step 3. Expected: both test files pass.

- [ ] **Step 6: Extend `.gitignore` and commit**

Append these exact entries:

```gitignore
.env
backend/.venv/
backend/data/
**/__pycache__/
.pytest_cache/
frontend/node_modules/
frontend/dist/
frontend/playwright-report/
```

```bash
git add .gitignore backend frontend
git commit -m "chore: scaffold quant research application"
```

---

### Task 2: 领域模型、代码规范化和 SQLite 增量缓存

**Files:**
- Create: `backend/src/quantlab/models.py`
- Create: `backend/src/quantlab/providers/base.py`
- Create: `backend/src/quantlab/cache.py`
- Create: `backend/tests/test_cache.py`

**Interfaces:**
- Consumes: `Settings.database_path`.
- Produces: `normalize_code(raw: str) -> str`, `Instrument`, `PriceBar`, `ResponseMeta`, `MarketCache.get_bars()`, `MarketCache.upsert_bars()`, `MarketCache.missing_ranges()`.

- [ ] **Step 1: Write failing domain and cache tests**

```python
# backend/tests/test_cache.py
from datetime import date
from quantlab.cache import MarketCache
from quantlab.models import PriceBar
from quantlab.providers.base import normalize_code

def bar(day: int, close: float) -> PriceBar:
    return PriceBar(
        code="512480.SH", trade_date=date(2026, 1, day),
        open=close, high=close + 0.02, low=close - 0.02,
        close=close, volume=1000, amount=1284,
        source="akshare", fetched_at="2026-08-08T00:00:00Z",
    )

def test_normalize_code_understands_shanghai_etf_and_stock():
    assert normalize_code("512480") == "512480.SH"
    assert normalize_code("600519.SH") == "600519.SH"

def test_cache_upserts_and_returns_sorted_bars(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.upsert_bars([bar(3, 1.30), bar(2, 1.28), bar(3, 1.31)])
    rows = cache.get_bars("512480.SH", date(2026, 1, 1), date(2026, 1, 3))
    assert [(row.trade_date.day, row.close) for row in rows] == [(2, 1.28), (3, 1.31)]

def test_missing_ranges_subtracts_synced_intervals(tmp_path):
    cache = MarketCache(tmp_path / "test.db")
    cache.mark_synced("512480.SH", date(2026, 1, 3), date(2026, 1, 7))
    assert cache.missing_ranges("512480.SH", date(2026, 1, 1), date(2026, 1, 10)) == [
        (date(2026, 1, 1), date(2026, 1, 2)),
        (date(2026, 1, 8), date(2026, 1, 10)),
    ]
```

- [ ] **Step 2: Run cache tests and verify RED**

Run: `cd backend && python -m pytest tests/test_cache.py -v`
Expected: FAIL because models, normalization and cache do not exist.

- [ ] **Step 3: Define exact domain models and Provider protocol**

```python
# backend/src/quantlab/models.py
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, Field

AssetType = Literal["etf", "equity"]

class Instrument(BaseModel):
    code: str
    name: str
    asset_type: AssetType
    exchange: Literal["SH", "SZ", "BJ"]

class PriceBar(BaseModel):
    code: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float | None = None
    source: str
    fetched_at: datetime

class ResponseMeta(BaseModel):
    sources: list[str]
    fetched_at: datetime
    cache_hit: bool
    is_demo: bool = False
    warnings: list[str] = Field(default_factory=list)
```

```python
# backend/src/quantlab/providers/base.py
from datetime import date
from typing import Protocol
from quantlab.models import Instrument, PriceBar

class MarketDataProvider(Protocol):
    name: str
    def search(self, query: str) -> list[Instrument]:
        raise NotImplementedError
    def get_instrument(self, code: str) -> Instrument:
        raise NotImplementedError
    def get_daily(self, code: str, start: date, end: date) -> list[PriceBar]:
        raise NotImplementedError

def normalize_code(raw: str) -> str:
    value = raw.strip().upper()
    if value.endswith((".SH", ".SZ", ".BJ")):
        digits, exchange = value.split(".", maxsplit=1)
        if len(digits) == 6 and digits.isdigit():
            return f"{digits}.{exchange}"
        raise ValueError("证券代码必须是 6 位数字或带交易所后缀的代码")
    if len(value) != 6 or not value.isdigit():
        raise ValueError("证券代码必须是 6 位数字或带交易所后缀的代码")
    if value[0] in "569":
        return f"{value}.SH"
    if value[0] in "013":
        return f"{value}.SZ"
    if value[0] in "48":
        return f"{value}.BJ"
    return f"{value}.SH"
```

- [ ] **Step 4: Implement SQLite schema and interval subtraction**

`MarketCache` must create `price_bars` with primary key `(code, trade_date)` and `sync_ranges` with `(code, start_date, end_date)`. `upsert_bars()` uses `INSERT ... ON CONFLICT DO UPDATE`; `get_bars()` orders ascending; `mark_synced()` merges touching/overlapping intervals before replacing them in one transaction; `missing_ranges()` returns inclusive uncovered ranges exactly as asserted above.

Use `sqlite3`, ISO date strings and `PriceBar.model_validate()`; do not introduce an ORM.

- [ ] **Step 5: Run cache tests and commit**

Run: `cd backend && python -m pytest tests/test_cache.py -v`
Expected: 3 tests PASS.

```bash
git add backend/src/quantlab/models.py backend/src/quantlab/providers/base.py backend/src/quantlab/cache.py backend/tests/test_cache.py
git commit -m "feat: add market domain and sqlite cache"
```

---

### Task 3: AkShare 与 Tushare 数据适配器

**Files:**
- Create: `backend/src/quantlab/providers/akshare_provider.py`
- Create: `backend/src/quantlab/providers/tushare_provider.py`
- Create: `backend/tests/test_providers.py`

**Interfaces:**
- Consumes: `normalize_code()`, `Instrument`, `PriceBar`, injected AkShare module or Tushare client.
- Produces: `AkShareProvider`, `TushareProvider` implementing `MarketDataProvider`; provider-specific failures raise `ProviderError(provider, code, reason)`.

- [ ] **Step 1: Write failing adapter contract tests with fixed in-memory responses**

```python
# backend/tests/test_providers.py
from datetime import date
import pandas as pd
from quantlab.providers.akshare_provider import AkShareProvider
from quantlab.providers.tushare_provider import TushareProvider

class FakeAk:
    def fund_etf_hist_em(self, **kwargs):
        assert kwargs["symbol"] == "512480"
        return pd.DataFrame([{
            "日期": "2026-01-05", "开盘": 1.20, "收盘": 1.25,
            "最高": 1.26, "最低": 1.19, "成交量": 100, "成交额": 125,
        }])

    def stock_zh_a_hist(self, **kwargs):
        assert kwargs["symbol"] == "600519"
        return pd.DataFrame([{
            "日期": "2026-01-05", "开盘": 1400.0, "收盘": 1410.0,
            "最高": 1420.0, "最低": 1390.0, "成交量": 50, "成交额": 70500,
        }])

class FakePro:
    def fund_daily(self, **kwargs):
        assert kwargs["ts_code"] == "512480.SH"
        return pd.DataFrame([{
            "ts_code": "512480.SH", "trade_date": "20260105",
            "open": 1.20, "high": 1.26, "low": 1.19, "close": 1.25,
            "vol": 100, "amount": 125,
        }])

    def daily(self, **kwargs):
        assert kwargs["ts_code"] == "600519.SH"
        return pd.DataFrame([{
            "ts_code": "600519.SH", "trade_date": "20260105",
            "open": 1400.0, "high": 1420.0, "low": 1390.0, "close": 1410.0,
            "vol": 50, "amount": 70500,
        }])

def assert_etf_bar(row):
    assert row.code == "512480.SH"
    assert row.trade_date == date(2026, 1, 5)
    assert (row.open, row.high, row.low, row.close) == (1.20, 1.26, 1.19, 1.25)

def test_akshare_maps_etf_daily():
    assert_etf_bar(AkShareProvider(FakeAk()).get_daily("512480.SH", date(2026, 1, 1), date(2026, 1, 6))[0])

def test_tushare_maps_etf_daily():
    assert_etf_bar(TushareProvider(FakePro()).get_daily("512480.SH", date(2026, 1, 1), date(2026, 1, 6))[0])

def test_akshare_uses_stock_endpoint_for_equity():
    row = AkShareProvider(FakeAk()).get_daily("600519.SH", date(2026, 1, 1), date(2026, 1, 6))[0]
    assert (row.code, row.close) == ("600519.SH", 1410.0)

def test_tushare_uses_daily_endpoint_for_equity():
    row = TushareProvider(FakePro()).get_daily("600519.SH", date(2026, 1, 1), date(2026, 1, 6))[0]
    assert (row.code, row.close) == ("600519.SH", 1410.0)
```

- [ ] **Step 2: Run provider tests and verify RED**

Run: `cd backend && python -m pytest tests/test_providers.py -v`
Expected: FAIL because both adapter modules are absent.

- [ ] **Step 3: Implement explicit field mapping**

`AkShareProvider.get_daily()` chooses `fund_etf_hist_em` for codes beginning with `5` or `1`, otherwise `stock_zh_a_hist`; pass `period="daily"`, `adjust="qfq"`, and compact `YYYYMMDD` dates. `TushareProvider.get_daily()` chooses `fund_daily` for ETF and `daily` for equity. Convert dates with `pandas.to_datetime`, sort ascending, drop duplicate trade dates keeping the last row, and attach an aware UTC `fetched_at`.

Wrap third-party exceptions as:

```python
class ProviderError(RuntimeError):
    def __init__(self, provider: str, code: str, reason: str):
        self.provider = provider
        self.code = code
        self.reason = reason
        super().__init__(f"{provider}:{code}:{reason}")
```

Do not log client objects or environment settings.

- [ ] **Step 4: Run adapter tests and commit**

Run: `cd backend && python -m pytest tests/test_providers.py -v`
Expected: ETF and equity adapter contract tests PASS.

```bash
git add backend/src/quantlab/providers backend/tests/test_providers.py
git commit -m "feat: add akshare and tushare adapters"
```

---

### Task 4: 数据质量、缓存编排、自动降级与交叉校验

**Files:**
- Create: `backend/src/quantlab/errors.py`
- Create: `backend/src/quantlab/services/quality.py`
- Create: `backend/src/quantlab/services/market_data.py`
- Create: `backend/tests/test_quality.py`
- Create: `backend/tests/test_market_data.py`

**Interfaces:**
- Consumes: `MarketCache`, `MarketDataProvider`, `PriceBar`.
- Produces: `validate_bars(bars) -> list[str]`, `MarketDataResult`, `MarketDataService.get_daily(code, start, end, refresh=False)`.

- [ ] **Step 1: Write failing quality tests**

```python
# backend/tests/test_quality.py
from datetime import date, datetime, timezone
from quantlab.models import PriceBar
from quantlab.services.quality import validate_bars

def test_quality_reports_invalid_ohlc_and_duplicate_dates():
    fetched = datetime.now(timezone.utc)
    rows = [
        PriceBar(code="512480.SH", trade_date=date(2026,1,5), open=1.2, high=1.1, low=1.15, close=1.3, volume=10, source="fake", fetched_at=fetched),
        PriceBar(code="512480.SH", trade_date=date(2026,1,5), open=1.2, high=1.3, low=1.1, close=1.2, volume=10, source="fake", fetched_at=fetched),
    ]
    warnings = validate_bars(rows)
    assert "DUPLICATE_TRADE_DATE:2026-01-05" in warnings
    assert "INVALID_OHLC:2026-01-05" in warnings
```

- [ ] **Step 2: Write failing fallback tests with fake providers**

```python
# backend/tests/test_market_data.py
from datetime import date, datetime, timedelta, timezone
import pytest
from quantlab.cache import MarketCache
from quantlab.models import PriceBar
from quantlab.providers.base import ProviderError
from quantlab.services.market_data import MarketDataService

class FakeProvider:
    def __init__(self, name, bars=None, error=None):
        self.name = name
        self.bars = bars or []
        self.error = error

    def get_daily(self, code, start, end):
        if self.error:
            raise ProviderError(self.name, code, self.error)
        return [row.model_copy(update={"source": self.name}) for row in self.bars if start <= row.trade_date <= end]

@pytest.fixture
def cache(tmp_path):
    return MarketCache(tmp_path / "market.db")

def make_bars(source="fake", close_offset=0.0):
    fetched = datetime(2026, 8, 8, tzinfo=timezone.utc)
    return [
        PriceBar(
            code="512480.SH", trade_date=date(2026, 1, 1) + timedelta(days=index),
            open=1.0 + index * 0.01, high=1.03 + index * 0.01,
            low=0.99 + index * 0.01, close=1.01 + index * 0.01 + close_offset,
            volume=1000 + index, amount=1000, source=source, fetched_at=fetched,
        )
        for index in range(25)
    ]

@pytest.fixture
def valid_bars():
    return make_bars()

@pytest.fixture
def primary_bars():
    return make_bars("akshare")

@pytest.fixture
def fallback_bars():
    return make_bars("tushare", close_offset=0.01)

def test_primary_failure_uses_fallback_and_reports_warning(cache, valid_bars):
    primary = FakeProvider("akshare", error="network unavailable")
    fallback = FakeProvider("tushare", bars=valid_bars)
    result = MarketDataService(cache, primary, fallback).get_daily(
        "512480", date(2026,1,1), date(2026,1,31)
    )
    assert result.meta.sources == ["tushare"]
    assert "PRIMARY_PROVIDER_FAILED" in result.meta.warnings
    assert result.bars == valid_bars

def test_both_fail_returns_cache_with_stale_warning(cache, valid_bars):
    cache.upsert_bars(valid_bars)
    service = MarketDataService(cache, FakeProvider("akshare", error="down"), FakeProvider("tushare", error="denied"))
    result = service.get_daily("512480.SH", date(2026,1,1), date(2026,1,31), refresh=True)
    assert result.meta.cache_hit is True
    assert "STALE_CACHE" in result.meta.warnings

def test_manual_refresh_cross_checks_last_twenty_sessions(cache, primary_bars, fallback_bars):
    result = MarketDataService(cache, FakeProvider("akshare", bars=primary_bars), FakeProvider("tushare", bars=fallback_bars)).get_daily(
        "512480.SH", date(2026,1,1), date(2026,3,31), refresh=True
    )
    assert any(item.startswith("SOURCE_DIFFERENCE:") for item in result.meta.warnings)
```

- [ ] **Step 3: Run service tests and verify RED**

Run: `cd backend && python -m pytest tests/test_quality.py tests/test_market_data.py -v`
Expected: FAIL because quality and orchestration services are absent.

- [ ] **Step 4: Implement validation and orchestration rules**

`validate_bars()` emits stable strings for duplicates, unsorted dates, missing numbers, negative volume, `high < low`, and close outside `[low, high]`. `MarketDataService` normalizes the code, queries `missing_ranges()`, fetches only uncovered intervals, validates before caching, and falls back when validation contains a fatal OHLC or missing-value warning.

On `refresh=True` with a fallback provider, fetch both sources for the last 20 available primary dates. Emit `SOURCE_DIFFERENCE:<date>:close` when absolute close difference exceeds `max(0.001, primary_close * 0.001)` and `SOURCE_DIFFERENCE:<date>:volume` when relative volume difference exceeds 5%. Keep primary values unless primary validation is fatal.

If both providers fail and cached bars exist, return them with `STALE_CACHE`; otherwise raise `DataUnavailableError(code, attempts)` without exposing credentials or raw client representations.

- [ ] **Step 5: Run all backend tests and commit**

Run: `cd backend && python -m pytest -v`
Expected: all current backend tests PASS.

```bash
git add backend/src/quantlab/errors.py backend/src/quantlab/services backend/tests/test_quality.py backend/tests/test_market_data.py
git commit -m "feat: add resilient market data service"
```

---

### Task 5: 技术指标、风险统计与透明评分

**Files:**
- Modify: `backend/src/quantlab/models.py`
- Create: `backend/src/quantlab/services/analytics.py`
- Create: `backend/tests/test_analytics.py`

**Interfaces:**
- Consumes: ascending `list[PriceBar]`, optional aligned benchmark bars, annual risk-free rate.
- Produces: `analyze_market(bars, benchmark_bars=None, risk_free_rate=0.02) -> AnalysisResult` with series, metrics, optional relative metrics and scored rules.

- [ ] **Step 1: Write failing deterministic analytics tests**

```python
# backend/tests/test_analytics.py
import math
import numpy as np
import pandas as pd
import pytest
from quantlab.services.analytics import max_drawdown, performance_metrics, technical_frame, score_diagnostics

def test_max_drawdown_uses_running_peak():
    drawdown, duration = max_drawdown(pd.Series([1.0, 1.2, 0.9, 1.1, 0.8]))
    assert drawdown == pytest.approx(-1 / 3)
    assert duration == 3

def test_performance_metrics_annualizes_daily_returns():
    metrics = performance_metrics(pd.Series([0.01, -0.005, 0.02]), risk_free_rate=0.0)
    expected_vol = pd.Series([0.01, -0.005, 0.02]).std(ddof=1) * math.sqrt(252)
    assert metrics.annualized_volatility == pytest.approx(expected_vol)

def test_technical_frame_has_declared_columns():
    close_series = pd.Series(np.linspace(1.0, 2.0, 90))
    frame = technical_frame(close_series)
    assert {"ma5", "ma10", "ma20", "ma60", "macd", "macd_signal", "macd_hist", "rsi14", "boll_upper", "boll_mid", "boll_lower"} <= set(frame.columns)

def test_scores_expose_points_and_triggered_rules():
    uptrend_frame = technical_frame(pd.Series(np.linspace(1.0, 2.0, 90)))
    scores = score_diagnostics(uptrend_frame)
    assert 0 <= scores.trend.score <= 100
    assert sum(rule.points for rule in scores.trend.rules if rule.triggered) == scores.trend.score
    assert {"trend", "momentum", "volatility", "drawdown"} == set(scores.model_dump())
```

- [ ] **Step 2: Run analytics tests and verify RED**

Run: `cd backend && python -m pytest tests/test_analytics.py -v`
Expected: FAIL because analytics functions are absent.

- [ ] **Step 3: Implement formulas with named outputs**

Implement vectorized Pandas calculations:

```python
returns = close.pct_change()
annualized_return = (1 + returns.dropna()).prod() ** (252 / len(returns.dropna())) - 1
annualized_volatility = returns.std(ddof=1) * np.sqrt(252)
downside = returns[returns < 0].std(ddof=1) * np.sqrt(252)
sharpe = (annualized_return - risk_free_rate) / annualized_volatility
sortino = (annualized_return - risk_free_rate) / downside
```

Use EMA spans 12/26/9 for MACD, Wilder-style exponential smoothing with alpha `1/14` for RSI, and 20-day rolling mean plus/minus two population standard deviations for Bollinger bands. Return `None` for undefined ratios rather than infinity.

When benchmark bars are supplied, inner-join returns by trade date. With at least 20 overlapping returns, compute `beta = covariance(asset, benchmark) / variance(benchmark)`, Pearson correlation, and compounded excess return `asset_cumulative - benchmark_cumulative`; otherwise return all three as `None` with warning `INSUFFICIENT_BENCHMARK_OVERLAP`.

Define trend score rules exactly: close above MA20 = 30, MA20 above MA60 = 30, five-session MA20 slope positive = 20, MACD histogram positive = 20. Define momentum score: RSI in `[45, 70]` = 35, 20-session return positive = 35, MACD above signal = 30. Define volatility score: 20-session annualized volatility below its 60-session median = 60 and lower than its value five sessions ago = 40. Define drawdown score: current drawdown above `-10%` = 40, maximum selected-range drawdown above `-20%` = 30, and longest drawdown duration at most 60 sessions = 30. Every rule carries label, points, triggered and explanation.

- [ ] **Step 4: Run analytics tests and commit**

Run: `cd backend && python -m pytest tests/test_analytics.py -v`
Expected: all analytics tests PASS.

```bash
git add backend/src/quantlab/models.py backend/src/quantlab/services/analytics.py backend/tests/test_analytics.py
git commit -m "feat: add transparent market analytics"
```

---

### Task 6: 无未来函数的双均线事件回测

**Files:**
- Modify: `backend/src/quantlab/models.py`
- Create: `backend/src/quantlab/services/backtest.py`
- Create: `backend/tests/test_backtest.py`

**Interfaces:**
- Consumes: `list[PriceBar]`, `BacktestRequest(code, start, end, fast_window, slow_window, fee_rate, slippage_rate, initial_cash)`; `start` and `end` are optional inside the pure engine because its bars are already sliced.
- Produces: `run_ma_cross(request, bars) -> BacktestResult` with curves, metrics and trades.

- [ ] **Step 1: Write failing execution-timing and cost tests**

```python
# backend/tests/test_backtest.py
from datetime import date, datetime, timedelta, timezone
import pytest
from quantlab.models import BacktestRequest, PriceBar
from quantlab.services.backtest import run_ma_cross

def crossing_bars():
    closes = [3.0, 2.0, 2.0, 4.0, 5.0, 2.0, 1.0, 1.0]
    fetched = datetime(2026, 8, 8, tzinfo=timezone.utc)
    return [
        PriceBar(
            code="512480.SH", trade_date=date(2026, 1, 1) + timedelta(days=index),
            open=close, high=close + 0.1, low=close - 0.1, close=close,
            volume=1000, amount=1000, source="fake", fetched_at=fetched,
        )
        for index, close in enumerate(closes)
    ]

def test_cross_signal_executes_at_next_open():
    bars = crossing_bars()
    result = run_ma_cross(
        BacktestRequest(code="512480.SH", fast_window=2, slow_window=3, fee_rate=0, slippage_rate=0, initial_cash=10_000),
        bars,
    )
    first_trade = result.trades[0]
    assert first_trade.signal_date == bars[3].trade_date
    assert first_trade.execution_date == bars[4].trade_date
    assert first_trade.execution_price == bars[4].open

def test_round_trip_deducts_fee_and_slippage():
    bars = crossing_bars()
    free = run_ma_cross(BacktestRequest(code="512480.SH", fast_window=2, slow_window=3, fee_rate=0, slippage_rate=0), bars)
    costly = run_ma_cross(BacktestRequest(code="512480.SH", fast_window=2, slow_window=3, fee_rate=0.001, slippage_rate=0.001), bars)
    assert costly.metrics.final_equity < free.metrics.final_equity

def test_rejects_fast_window_not_less_than_slow_window():
    with pytest.raises(ValueError, match="快线周期必须小于慢线周期"):
        run_ma_cross(BacktestRequest(code="512480.SH", fast_window=20, slow_window=20), crossing_bars())
```

- [ ] **Step 2: Run backtest tests and verify RED**

Run: `cd backend && python -m pytest tests/test_backtest.py -v`
Expected: FAIL because request/result models and engine are absent.

- [ ] **Step 3: Implement the event loop**

Add the request boundary with exact defaults:

```python
class BacktestRequest(BaseModel):
    code: str
    start: date | None = None
    end: date | None = None
    fast_window: int = Field(default=20, ge=2, le=120)
    slow_window: int = Field(default=60, ge=3, le=250)
    fee_rate: float = Field(default=0.0003, ge=0, le=0.02)
    slippage_rate: float = Field(default=0.0002, ge=0, le=0.02)
    initial_cash: float = Field(default=100_000, gt=0)
```

Generate signals from close-based rolling means, queue each crossing for the next row, and execute at `next_open * (1 + slippage)` for buys or `next_open * (1 - slippage)` for sells. Deduct `trade_value * fee_rate`, allow fractional shares for research consistency, and mark equity at each close. Buy-and-hold starts at the first strategy performance day opening and uses the same costs.

Store each trade with signal date, execution date, side, execution price, quantity, fee and post-trade cash. Compute performance with the Task 5 metric helpers. Define trade win rate only from completed buy/sell round trips; return `None` when none are completed.

- [ ] **Step 4: Run backtest tests and commit**

Run: `cd backend && python -m pytest tests/test_backtest.py -v`
Expected: all backtest tests PASS.

```bash
git add backend/src/quantlab/models.py backend/src/quantlab/services/backtest.py backend/tests/test_backtest.py
git commit -m "feat: add next-session moving average backtest"
```

---

### Task 7: 资产资料服务与完整 FastAPI 契约

**Files:**
- Create: `backend/src/quantlab/services/assets.py`
- Create: `backend/src/quantlab/api/dependencies.py`
- Create: `backend/src/quantlab/api/instruments.py`
- Create: `backend/src/quantlab/api/market.py`
- Create: `backend/src/quantlab/api/backtests.py`
- Modify: `backend/src/quantlab/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_assets.py`
- Create: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: market, analytics, asset and backtest services.
- Produces: dependency accessors `get_market_data_service()`, `get_asset_service()`, `get_backtest_service()`; all endpoints from design section 8 with `Envelope[T] { data, meta }` and stable error shapes.

- [ ] **Step 1: Write failing asset-type tests**

```python
# backend/tests/test_assets.py
from datetime import date
from quantlab.models import Instrument
from quantlab.services.assets import AssetService

class FakeProfileProvider:
    def get_instrument(self, code):
        if code == "512480.SH":
            return Instrument(code=code, name="半导体 ETF", asset_type="etf", exchange="SH")
        return Instrument(code=code, name="贵州茅台", asset_type="equity", exchange="SH")

    def get_etf_profile(self, code):
        return {"tracking_index": "中证全指半导体产品与设备指数", "holdings": [{"name": "样本公司", "weight": 0.10}]}

    def get_equity_profile(self, code):
        return {"industry": "食品饮料", "financial_periods": [{"report_date": date(2026, 3, 31), "revenue": 1.0, "net_profit": 0.5}]}

def test_etf_profile_contains_tracking_and_holdings():
    profile = AssetService(FakeProfileProvider()).get_profile("512480.SH")
    assert profile.asset_type == "etf"
    assert profile.etf.tracking_index
    assert profile.equity is None

def test_equity_profile_contains_report_dates():
    profile = AssetService(FakeProfileProvider()).get_profile("600519.SH")
    assert profile.asset_type == "equity"
    assert profile.equity.financial_periods[0].report_date
    assert profile.etf is None
```

- [ ] **Step 2: Write failing API contract tests with dependency overrides**

In `backend/tests/conftest.py`, define `FullFakeProvider` with `name = "fake"` and methods `search(query)`, `get_instrument(code)`, `get_daily(code, start, end)`, `get_etf_profile(code)` and `get_equity_profile(code)`. `get_daily` returns 100 monotonically dated valid bars; the profile methods return the same values used in `test_assets.py`. The `client(tmp_path)` fixture constructs real `MarketCache`, `MarketDataService`, `AssetService`, analytics and backtest services around that fake, then overrides `get_market_data_service`, `get_asset_service` and `get_backtest_service` on `create_app()` before returning `TestClient(app)`. This keeps every API test offline while exercising real routing and calculation code.

```python
# backend/tests/test_api.py
def test_market_daily_wraps_data_and_provenance(client):
    response = client.get("/api/market/512480/daily?start=2026-01-01&end=2026-03-31")
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["code"] == "512480.SH"
    assert body["meta"]["sources"] == ["fake"]
    assert body["meta"]["is_demo"] is False

def test_invalid_code_has_stable_error_shape(client):
    response = client.get("/api/instruments/not-a-code")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_INSTRUMENT_CODE"

def test_backtest_rejects_invalid_windows(client):
    response = client.post("/api/backtests/ma-cross", json={"code":"512480.SH", "fast_window":60, "slow_window":20})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_BACKTEST_PARAMETERS"
```

- [ ] **Step 3: Run asset/API tests and verify RED**

Run: `cd backend && python -m pytest tests/test_assets.py tests/test_api.py -v`
Expected: FAIL because services and routes are absent.

- [ ] **Step 4: Implement asset profiles and dependency wiring**

Extend provider capabilities with optional `get_etf_profile(code)` and `get_equity_profile(code)`. The asset service first resolves `Instrument.asset_type`, calls only the matching profile method, and converts permissions failures to a field-level `availability` object with `status="unavailable"` and a Chinese reason. Financial values include `report_date`; valuation values include `trade_date`.

For AkShare, use `fund_etf_spot_em` for ETF lookup/current fund fields, `fund_portfolio_hold_em` for disclosed holdings, `stock_individual_info_em` for company identity, `stock_zh_valuation_baidu` for dated valuation and `stock_financial_abstract_ths` for reporting-period summaries. For Tushare, use `fund_basic`, `fund_share`, `fund_portfolio`, `stock_basic`, `daily_basic`, `income` and `fina_indicator`. Normalize percentage weights to decimals in `[0, 1]`, preserve source report/trade dates, cap holdings at ten, and translate missing interface permission into `Availability(status="unavailable", reason="当前数据源权限不足")` without failing the full profile.

`AssetService.get_profile(code, market_bars=None, benchmark_bars=None)` computes 20-session size/share percentage changes when histories exist, premium as `close / nav - 1` when same-date close and NAV exist, and annualized tracking deviation as the standard deviation of aligned ETF-minus-index daily returns times `sqrt(252)` when at least 20 overlaps exist. It leaves each derived value as `None` when its inputs are unavailable and preserves a field-level reason.

Add these model boundaries to `models.py`:

```python
class Availability(BaseModel):
    status: Literal["available", "unavailable"]
    reason: str | None = None

class Holding(BaseModel):
    code: str | None = None
    name: str
    weight: float = Field(ge=0, le=1)

class EtfProfile(BaseModel):
    tracking_index: str | None = None
    tracking_index_code: str | None = None
    manager: str | None = None
    inception_date: date | None = None
    size: float | None = None
    shares: float | None = None
    size_change_20d: float | None = None
    share_change_20d: float | None = None
    turnover_rate: float | None = None
    nav: float | None = None
    premium_rate: float | None = None
    tracking_deviation: float | None = None
    holdings: list[Holding] = Field(default_factory=list)
    availability: Availability

class FinancialPeriod(BaseModel):
    report_date: date
    revenue: float | None = None
    revenue_yoy: float | None = None
    net_profit: float | None = None
    net_profit_yoy: float | None = None
    roe: float | None = None
    gross_margin: float | None = None
    net_margin: float | None = None
    debt_ratio: float | None = None

class EquityProfile(BaseModel):
    industry: str | None = None
    valuation_trade_date: date | None = None
    pe: float | None = None
    pb: float | None = None
    total_market_cap: float | None = None
    float_market_cap: float | None = None
    financial_periods: list[FinancialPeriod] = Field(default_factory=list)
    availability: Availability

class AssetProfile(BaseModel):
    code: str
    asset_type: AssetType
    etf: EtfProfile | None = None
    equity: EquityProfile | None = None
```

`dependencies.py` constructs one SQLite cache, AkShare provider, optional Tushare provider, and the four services from `get_settings()`. Keep dependency accessors as functions so tests can override them without network access.

- [ ] **Step 5: Implement routers and stable errors**

Register these exact routes:

```text
GET  /api/instruments/search?q=
GET  /api/instruments/{code}
GET  /api/market/{code}/daily?start=&end=
GET  /api/analysis/{code}?start=&end=
GET  /api/etf/{code}
GET  /api/equity/{code}
POST /api/backtests/ma-cross
POST /api/data/{code}/refresh
GET  /api/health
```

Use a global exception handler returning:

```json
{
  "error": {
    "code": "DATA_UNAVAILABLE",
    "message": "暂时无法获取 512480.SH 的数据",
    "action": "请稍后重试，或配置 TUSHARE_TOKEN 启用备用数据源"
  }
}
```

Reject start after end, ranges shorter than the slow-window warmup, invalid security codes, negative costs, and unsupported asset-type routes.

For ETF analysis, resolve the profile first; when `tracking_index_code` is present, fetch matching benchmark bars and pass them to `analyze_market`. For ordinary stocks and ETFs without a resolvable index code, return relative metrics as unavailable rather than substituting an unrelated market index.

- [ ] **Step 6: Run backend suite and commit**

Run: `cd backend && python -m pytest --cov=quantlab --cov-report=term-missing`
Expected: all tests PASS; new service and API modules have exercised success and failure branches.

```bash
git add backend/src/quantlab backend/tests/conftest.py backend/tests/test_assets.py backend/tests/test_api.py
git commit -m "feat: expose research and backtest API"
```

---

### Task 8: “研究手记”前端数据层与研究台主体

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/hooks/useResearch.ts`
- Create: `frontend/src/components/Header.tsx`
- Create: `frontend/src/components/InstrumentHero.tsx`
- Create: `frontend/src/components/DataProvenance.tsx`
- Create: `frontend/src/components/StatePanel.tsx`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/app.css`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`
- Create: `frontend/src/__tests__/fixtures.ts`
- Modify: `frontend/src/__tests__/App.test.tsx`

**Interfaces:**
- Consumes: Task 7 REST envelopes.
- Produces: `api.searchInstruments`, `api.loadResearch`, `useResearch()` and the responsive page shell.

- [ ] **Step 1: Define TypeScript contracts to mirror the API**

`types.ts` must define `Instrument`, `PriceBar`, `AnalysisResult`, `AssetProfile`, `BacktestRequest`, `BacktestResult`, `ResponseMeta`, `Envelope<T>`, `ApiError` and `DateRange { start: string; end: string; key: '3m' | '6m' | '1y' | '3y' | 'all' }`. Use ISO date strings at the API boundary and never use `any`.

The client exposes:

```ts
export interface ResearchBundle {
  instrument: Envelope<Instrument>
  market: Envelope<PriceBar[]>
  analysis: Envelope<AnalysisResult>
  profile: Envelope<AssetProfile>
}

export const api = {
  searchInstruments(query: string): Promise<Envelope<Instrument[]>>,
  loadResearch(code: string, range: DateRange): Promise<ResearchBundle>,
  refresh(code: string): Promise<Envelope<{ refreshed: boolean }>>,
  runBacktest(request: BacktestRequest): Promise<Envelope<BacktestResult>>,
}
```

- [ ] **Step 2: Write failing shell behavior tests**

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import App from '../App'
import { api } from '../api/client'
import { researchBundle } from './fixtures'

vi.mock('../api/client', () => ({
  api: {
    searchInstruments: vi.fn(),
    loadResearch: vi.fn(),
    refresh: vi.fn(),
    runBacktest: vi.fn(),
  },
}))

beforeEach(() => {
  vi.mocked(api.loadResearch).mockResolvedValue(researchBundle)
})

it('loads the default ETF and shows provenance', async () => {
  render(<App />)
  expect(await screen.findByRole('heading', { name: /半导体 ETF/ })).toBeInTheDocument()
  expect(screen.getByText('AkShare')).toBeInTheDocument()
  expect(screen.getByText(/更新于/)).toBeInTheDocument()
})

it('keeps current research visible when a new code is invalid', async () => {
  vi.mocked(api.searchInstruments).mockRejectedValueOnce(new Error('请输入 6 位证券代码'))
  render(<App />)
  await screen.findByRole('heading', { name: /半导体 ETF/ })
  await userEvent.type(screen.getByLabelText('证券代码或名称'), 'bad-code{enter}')
  expect(screen.getByRole('heading', { name: /半导体 ETF/ })).toBeInTheDocument()
  expect(screen.getByText(/请输入 6 位证券代码/)).toBeInTheDocument()
})
```

Create `fixtures.ts` exporting fully typed `researchBundle`, `bars`, `analysis`, `etfProfile`, `equityProfile` and `backtestResult`. Use two bars dated `2026-01-05` and `2026-01-06`, `sources: ['AkShare']`, `is_demo: false`, ETF name `半导体 ETF`, tracking index `中证全指半导体产品与设备指数`, and one buy/sell round trip. Reuse these factories in Tasks 9 and 10 so component tests share one contract fixture.

- [ ] **Step 3: Run frontend shell tests and verify RED**

Run: `cd frontend && npm test -- --run src/__tests__/App.test.tsx`
Expected: FAIL because client, hook and components do not exist.

- [ ] **Step 4: Implement loading/state behavior and visual tokens**

`useResearch()` defaults to `{ code: '512480.SH', range: '1y' }`, fetches the four research requests concurrently, aborts stale requests on code/range changes, and preserves the last successful bundle when refresh/search fails. Expose `status: 'idle' | 'loading' | 'ready' | 'refreshing' | 'error'` and an actionable Chinese error string.

Render range controls `3月`, `6月`, `1年`, `3年`, `全部`, mapped to `3m | 6m | 1y | 3y | all`; convert each choice to explicit start/end dates before calling the API. A range change reloads market, analysis and profile-derived interval metrics while preserving the selected instrument.

Use these exact CSS variables:

```css
:root {
  --paper: #f5f1e8;
  --surface: #fffdf7;
  --ink: #24231f;
  --muted: #777167;
  --accent: #d55331;
  --positive: #167a58;
  --negative: #bd3f34;
  --line: #d9d2c4;
  --radius-lg: 22px;
  --radius-md: 14px;
  --shadow: 0 18px 60px rgb(70 55 35 / 8%);
}
```

The desktop content max-width is `1440px`; use a 12-column grid above `960px` and one column below. Header search is keyboard-submit capable. Skeletons must reserve the same major dimensions as loaded cards. Always render the disclaimer in the footer.

- [ ] **Step 5: Run tests and commit**

Run: `cd frontend && npm test -- --run src/__tests__/App.test.tsx`
Expected: shell behavior tests PASS.

```bash
git add frontend
git commit -m "feat: build research notebook application shell"
```

---

### Task 9: ECharts 行情、量化诊断和资产自适应展示

**Files:**
- Create: `frontend/src/components/MarketChart.tsx`
- Create: `frontend/src/components/MetricGrid.tsx`
- Create: `frontend/src/components/AssetProfile.tsx`
- Create: `frontend/src/__tests__/MarketChart.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles/app.css`

**Interfaces:**
- Consumes: `PriceBar[]`, `AnalysisResult`, `AssetProfile`, selected overlays and time range.
- Produces: linked K-line/volume chart, transparent metric cards, ETF/equity-specific profile panels.

- [ ] **Step 1: Write failing chart and profile tests**

Mock ECharts initialization and assert the generated option rather than canvas pixels:

```tsx
import { render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import MarketChart from '../components/MarketChart'
import AssetProfile from '../components/AssetProfile'
import { analysis, bars, equityProfile, etfProfile } from './fixtures'

const { mockedSetOption } = vi.hoisted(() => ({ mockedSetOption: vi.fn() }))
vi.mock('echarts', () => ({
  init: () => ({ setOption: mockedSetOption, resize: vi.fn(), dispose: vi.fn() }),
}))

it('links candlestick and volume to the same zoom range', () => {
  render(<MarketChart bars={bars} analysis={analysis} overlays={['ma20', 'macd']} />)
  const option = mockedSetOption.mock.calls.at(-1)?.[0]
  expect(option.series.some((item: { type: string }) => item.type === 'candlestick')).toBe(true)
  expect(option.dataZoom).toHaveLength(2)
  expect(option.axisPointer.link).toEqual([{ xAxisIndex: 'all' }])
})

it('shows ETF holdings and hides equity financials', () => {
  render(<AssetProfile profile={etfProfile} />)
  expect(screen.getByText('前十大持仓')).toBeInTheDocument()
  expect(screen.queryByText('营业收入')).not.toBeInTheDocument()
})

it('shows report dates for equity financials', () => {
  render(<AssetProfile profile={equityProfile} />)
  expect(screen.getByText('营业收入')).toBeInTheDocument()
  expect(screen.getByText('报告期 2026-03-31')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run component tests and verify RED**

Run: `cd frontend && npm test -- --run src/__tests__/MarketChart.test.tsx`
Expected: FAIL because chart and profile components are absent.

- [ ] **Step 3: Implement the ECharts option and lifecycle**

Create the chart once in `useEffect`, call `resize()` through `ResizeObserver`, and dispose it on unmount. Build aligned category axes for candlestick, volume and the selected lower indicator. Use ECharts dataZoom inside and slider, linked axis pointers, `animation: false` for more than 1,000 bars, red `#D55331` for rising candles and green `#167A58` for falling candles, matching Chinese market convention.

Overlay controls support `ma5`, `ma10`, `ma20`, `ma60`, `boll`, `macd`, `rsi`. MACD and RSI occupy the lower pane one at a time; MA and Bollinger remain on the price pane. Tooltip prints date, OHLC, volume and selected indicator values.

- [ ] **Step 4: Implement metric and asset panels**

`MetricGrid` groups annualized return/volatility, Sharpe, Sortino, maximum drawdown and drawdown duration. When annualization uses less than 252 valid returns, render `短样本年化`. Each trend/momentum/volatility/drawdown card expands to show rule label, awarded points and explanation.

`AssetProfile` branches only on `profile.asset_type`; ETF renders tracking index, size/share, liquidity and top holdings concentration; equity renders valuation date plus four reporting periods. Unavailable fields render their server-provided reason.

- [ ] **Step 5: Run frontend tests and commit**

Run: `cd frontend && npm test -- --run`
Expected: all frontend tests PASS.

```bash
git add frontend/src
git commit -m "feat: visualize market analytics and asset profiles"
```

---

### Task 10: 策略实验室、真实数据 smoke 与端到端验收

**Files:**
- Create: `backend/src/quantlab/providers/demo_provider.py`
- Create: `frontend/src/components/BacktestLab.tsx`
- Create: `frontend/src/__tests__/BacktestLab.test.tsx`
- Create: `frontend/e2e/research.spec.ts`
- Create: `frontend/playwright.config.ts`
- Modify: `frontend/package.json`
- Create: `scripts/smoke_live_data.py`
- Create: `.env.example`
- Create: `Makefile`
- Create: `README.md`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: an `onRun(request) -> Promise<BacktestResult>` callback; `App` implements it by awaiting `api.runBacktest(request)` and returning `envelope.data`.
- Produces: interactive strategy lab, live provider smoke command, one-command local startup and end-to-end acceptance proof.

- [ ] **Step 1: Write failing strategy-lab tests**

```tsx
// frontend/src/__tests__/BacktestLab.test.tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import BacktestLab from '../components/BacktestLab'
import { backtestResult } from './fixtures'

it('blocks an invalid moving-average pair before requesting', async () => {
  const onRun = vi.fn()
  render(<BacktestLab code="512480.SH" start="2025-08-08" end="2026-08-08" onRun={onRun} />)
  await userEvent.clear(screen.getByLabelText('快线周期'))
  await userEvent.type(screen.getByLabelText('快线周期'), '60')
  await userEvent.clear(screen.getByLabelText('慢线周期'))
  await userEvent.type(screen.getByLabelText('慢线周期'), '20')
  await userEvent.click(screen.getByRole('button', { name: '运行回测' }))
  expect(screen.getByText('快线周期必须小于慢线周期')).toBeInTheDocument()
  expect(onRun).not.toHaveBeenCalled()
})

it('renders strategy and buy-hold metrics with trade dates', async () => {
  render(<BacktestLab code="512480.SH" start="2025-08-08" end="2026-08-08" onRun={async () => backtestResult} />)
  await userEvent.click(screen.getByRole('button', { name: '运行回测' }))
  expect(await screen.findByText('策略净值')).toBeInTheDocument()
  expect(screen.getByText('买入并持有')).toBeInTheDocument()
  expect(screen.getByText(/信号日/)).toBeInTheDocument()
  expect(screen.getByText(/执行日/)).toBeInTheDocument()
})
```

- [ ] **Step 2: Run strategy tests and verify RED**

Run: `cd frontend && npm test -- --run src/__tests__/BacktestLab.test.tsx`
Expected: FAIL because `BacktestLab` is absent.

- [ ] **Step 3: Implement strategy form and result charts**

`BacktestLab` accepts `code`, `start`, `end` and `onRun`, and includes the selected research interval in every request. Default values: fast 20, slow 60, fee 0.0003, slippage 0.0002, initial cash 100000. Validate fast in `[2, 120]`, slow in `[3, 250]`, fast < slow, and each cost in `[0, 0.02]`. Disable submission during a request while preserving previous results on failure.

Use one ECharts view for strategy and buy-hold normalized equity, plus a lower drawdown pane. Render performance comparison and a trade table with signal date, execution date, side, price, quantity and fee. Place an always-visible sentence above results: `历史回测不代表未来表现；参数越多，过拟合风险越高。`

- [ ] **Step 4: Add a deterministic end-to-end test**

Install Playwright and add an E2E test that runs against the backend in demo fixture mode:

```bash
cd frontend
npm install -D @playwright/test
npx playwright install chromium
```

```ts
import { expect, test } from '@playwright/test'

test('completes the default 512480 research flow', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: /半导体 ETF/ })).toBeVisible()
  await expect(page.getByText('演示数据')).toBeVisible()
  await expect(page.getByTestId('market-chart')).toBeVisible()
  await page.getByRole('button', { name: '运行回测' }).click()
  await expect(page.getByText('策略净值')).toBeVisible()
  await expect(page.getByText('仅供个人研究学习，不构成投资建议')).toBeVisible()
})
```

Configure Playwright `webServer` entries for `uvicorn quantlab.main:app --app-dir backend/src --port 8000` and `npm run dev -- --host 127.0.0.1`, with `QUANTLAB_DEMO_MODE=1` only in the backend E2E process.

`DemoProvider` must generate 320 weekday bars from `2025-01-02` using a deterministic close formula `1.0 + index * 0.001 + sin(index / 9) * 0.04`, fixed positive volume, and OHLC values enclosing close. It returns the 512480 ETF instrument/profile used by component fixtures and sets provider name to `demo`. In `dependencies.py`, select it only when `settings.demo_mode is True`; ensure `ResponseMeta.is_demo` is derived from the selected provider name and not from request input.

- [ ] **Step 5: Add live-data smoke without silent demo fallback**

`scripts/smoke_live_data.py` constructs production dependencies with demo mode off, requests the last 120 calendar days for `512480.SH`, and exits non-zero unless it receives at least 40 sorted, quality-valid bars with `is_demo is False`. Print only code, row count, first/last trade dates, provider names and warnings; never print settings or tokens.

Run: `python scripts/smoke_live_data.py`
Expected with network access: one line built by `f"512480.SH rows={len(bars)} range={bars[0].trade_date}..{bars[-1].trade_date} sources={','.join(meta.sources)}"` and exit 0. If both providers are externally unavailable, report their sanitized failure reasons and keep this result distinct from the deterministic test suite.

- [ ] **Step 6: Add one-command workflows and documentation**

Create `Makefile` targets:

```make
install:
	python -m venv backend/.venv
	backend/.venv/bin/pip install -e 'backend[dev]'
	cd frontend && npm install

dev-api:
	backend/.venv/bin/uvicorn quantlab.main:app --app-dir backend/src --reload --port 8000

dev-web:
	cd frontend && npm run dev -- --host 127.0.0.1

dev:
	@$(MAKE) dev-api & api_pid=$$!; $(MAKE) dev-web & web_pid=$$!; trap 'kill $$api_pid $$web_pid 2>/dev/null' EXIT INT TERM; wait

test:
	backend/.venv/bin/python -m pytest backend/tests
	cd frontend && npm test -- --run

smoke-live:
	backend/.venv/bin/python scripts/smoke_live_data.py
```

README must document prerequisites, `make install`, one-command `make dev` startup, separate `make dev-api`/`make dev-web` troubleshooting, optional `TUSHARE_TOKEN`, demo mode, data-source precedence, indicator/backtest formulas, known API permission limits, testing commands and the research-only disclaimer. `.env.example` contains only:

```dotenv
TUSHARE_TOKEN=
QUANTLAB_DATABASE_PATH=./backend/data/quantlab.db
QUANTLAB_DEMO_MODE=0
QUANTLAB_FRONTEND_ORIGIN=http://localhost:5173
```

- [ ] **Step 7: Run final verification**

Run in order:

```bash
make test
cd frontend && npx playwright test
cd ..
make smoke-live
```

Expected: unit/integration suites pass; E2E default flow passes in explicit demo mode; live smoke either proves current real data with exit 0 or reports an external provider/network blocker without substituting demo data.

- [ ] **Step 8: Inspect responsive UI and commit**

Start both dev services, use browser automation at 1440×1000 and 390×844, and verify no horizontal overflow; inspect loading, ready, invalid-code, source-warning, unavailable-profile and backtest-result states. Save screenshots under a temporary ignored directory, not source control.

```bash
git add .env.example Makefile README.md frontend scripts
git commit -m "feat: complete quant research prototype"
```

---

## Spec Coverage Map

- Architecture, modular boundaries and local storage: Tasks 1–4.
- AkShare/Tushare acquisition, provenance, cache, quality and fallback: Tasks 2–4 and Task 10 smoke.
- Technical indicators, transparent scores and risk metrics: Task 5 and Task 9.
- ETF profile and ordinary A-share fundamentals: Task 7 and Task 9.
- Next-session, cost-aware dual-moving-average backtest: Task 6 and Task 10.
- Research-notebook visual direction, responsive behavior and all UI states: Tasks 8–10.
- Security, explicit demo mode, disclaimers and configuration: Tasks 1, 7, 8 and 10.
- Unit, integration, component, end-to-end and live-provider verification: every task, finalized in Task 10.
