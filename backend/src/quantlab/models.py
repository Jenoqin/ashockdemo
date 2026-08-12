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

class ScoreRule(BaseModel):
    label: str
    points: int
    triggered: bool
    explanation: str

class DiagnosticCategory(BaseModel):
    score: int
    rules: list[ScoreRule]

class Diagnostics(BaseModel):
    trend: DiagnosticCategory
    momentum: DiagnosticCategory
    volatility: DiagnosticCategory
    drawdown: DiagnosticCategory

class PerformanceMetrics(BaseModel):
    annualized_return: float | None = None
    annualized_volatility: float | None = None
    downside: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    beta: float | None = None
    correlation: float | None = None
    excess_return: float | None = None

class AnalysisResult(BaseModel):
    metrics: PerformanceMetrics
    diagnostics: Diagnostics

class BacktestRequest(BaseModel):
    code: str
    start: date | None = None
    end: date | None = None
    fast_window: int = 20
    slow_window: int = 60
    fee_rate: float = 0.0001
    slippage_rate: float = 0.001
    initial_cash: float = 100000.0

class TradeRecord(BaseModel):
    signal_date: date
    execution_date: date
    direction: Literal["long", "close"]
    execution_price: float
    volume: float
    fee: float
    slippage: float

class BacktestMetrics(BaseModel):
    final_equity: float
    annualized_return: float | None = None
    annualized_volatility: float | None = None
    sharpe: float | None = None
    max_drawdown: float | None = None
    trades_count: int
    win_rate: float | None = None

class BacktestResult(BaseModel):
    request: BacktestRequest
    metrics: BacktestMetrics
    trades: list[TradeRecord]
    equity_curve: list[dict]
