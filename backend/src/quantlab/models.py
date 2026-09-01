from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import BaseModel, Field, model_validator

AssetType = Literal["etf", "equity"]
PositiveFiniteFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegativeFiniteFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]

class Instrument(BaseModel):
    code: str
    name: str
    full_name: str | None = None
    asset_type: AssetType
    exchange: Literal["SH", "SZ", "BJ"]

class PriceBar(BaseModel):
    code: str
    trade_date: date
    open: PositiveFiniteFloat
    high: PositiveFiniteFloat
    low: PositiveFiniteFloat
    close: PositiveFiniteFloat
    volume: NonNegativeFiniteFloat
    amount: NonNegativeFiniteFloat | None = None
    source: str
    fetched_at: datetime

    @model_validator(mode="after")
    def validate_ohlc_relationships(self):
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        tolerance = 1e-5
        if not self.low - tolerance <= self.open <= self.high + tolerance:
            raise ValueError("open must be within the low/high range")
        if not self.low - tolerance <= self.close <= self.high + tolerance:
            raise ValueError("close must be within the low/high range")
        return self

class ResponseMeta(BaseModel):
    sources: list[str]
    fetched_at: datetime
    cache_hit: bool
    data_end_date: date | None = None
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
    period_return: float | None = None
    annualized_return: float | None = None
    annualized_volatility: float | None = None
    downside: float | None = None
    sharpe: float | None = None
    sortino: float | None = None
    max_drawdown: float | None = None
    max_drawdown_duration: int | None = None
    current_drawdown: float | None = None
    beta: float | None = None
    correlation: float | None = None
    excess_return: float | None = None

class AnalysisSeries(BaseModel):
    dates: list[date] = Field(default_factory=list)
    cumulative_return: list[float | None] = Field(default_factory=list)
    benchmark_return: list[float | None] = Field(default_factory=list)
    drawdown: list[float | None] = Field(default_factory=list)
    rolling_volatility: list[float | None] = Field(default_factory=list)
    rolling_sharpe: list[float | None] = Field(default_factory=list)
    ma20: list[float | None] = Field(default_factory=list)
    ma60: list[float | None] = Field(default_factory=list)
    macd: list[float | None] = Field(default_factory=list)
    macd_signal: list[float | None] = Field(default_factory=list)
    macd_hist: list[float | None] = Field(default_factory=list)
    rsi14: list[float | None] = Field(default_factory=list)
    return_20d: list[float | None] = Field(default_factory=list)
    boll_upper: list[float | None] = Field(default_factory=list)
    boll_mid: list[float | None] = Field(default_factory=list)
    boll_lower: list[float | None] = Field(default_factory=list)
    atr14_percent: list[float | None] = Field(default_factory=list)

class AnalysisResult(BaseModel):
    metrics: PerformanceMetrics
    diagnostics: Diagnostics
    series: AnalysisSeries = Field(default_factory=AnalysisSeries)

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
    turnover_rate: float | None = None
    financial_periods: list[FinancialPeriod] = Field(default_factory=list)
    availability: Availability

class AssetProfile(BaseModel):
    code: str
    asset_type: AssetType
    etf: EtfProfile | None = None
    equity: EquityProfile | None = None
