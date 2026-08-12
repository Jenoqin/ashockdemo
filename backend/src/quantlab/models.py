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
