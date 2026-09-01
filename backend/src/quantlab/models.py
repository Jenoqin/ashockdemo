import math
from datetime import date, datetime
from typing import Annotated, Literal
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

AssetType = Literal["etf", "equity"]
PositiveFiniteFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]
NonNegativeFiniteFloat = Annotated[float, Field(ge=0, allow_inf_nan=False)]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
PositiveWindow = Annotated[int, Field(strict=True, gt=0)]
FeeRate = Annotated[float, Field(ge=0, le=0.1, allow_inf_nan=False)]
SlippageRate = Annotated[float, Field(ge=0, lt=1, allow_inf_nan=False)]


def finite_float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be numeric") from exc
    return number if math.isfinite(number) else None


OptionalFiniteFloat = Annotated[
    FiniteFloat | None,
    BeforeValidator(finite_float_or_none),
]

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
    model_config = ConfigDict(validate_assignment=True)

    period_return: OptionalFiniteFloat = None
    annualized_return: OptionalFiniteFloat = None
    annualized_volatility: OptionalFiniteFloat = None
    downside: OptionalFiniteFloat = None
    sharpe: OptionalFiniteFloat = None
    sortino: OptionalFiniteFloat = None
    max_drawdown: OptionalFiniteFloat = None
    max_drawdown_duration: int | None = None
    current_drawdown: OptionalFiniteFloat = None
    beta: OptionalFiniteFloat = None
    correlation: OptionalFiniteFloat = None
    excess_return: OptionalFiniteFloat = None

class AnalysisSeries(BaseModel):
    dates: list[date] = Field(default_factory=list)
    cumulative_return: list[OptionalFiniteFloat] = Field(default_factory=list)
    benchmark_return: list[OptionalFiniteFloat] = Field(default_factory=list)
    drawdown: list[OptionalFiniteFloat] = Field(default_factory=list)
    rolling_volatility: list[OptionalFiniteFloat] = Field(default_factory=list)
    rolling_sharpe: list[OptionalFiniteFloat] = Field(default_factory=list)
    ma20: list[OptionalFiniteFloat] = Field(default_factory=list)
    ma60: list[OptionalFiniteFloat] = Field(default_factory=list)
    macd: list[OptionalFiniteFloat] = Field(default_factory=list)
    macd_signal: list[OptionalFiniteFloat] = Field(default_factory=list)
    macd_hist: list[OptionalFiniteFloat] = Field(default_factory=list)
    rsi14: list[OptionalFiniteFloat] = Field(default_factory=list)
    return_20d: list[OptionalFiniteFloat] = Field(default_factory=list)
    boll_upper: list[OptionalFiniteFloat] = Field(default_factory=list)
    boll_mid: list[OptionalFiniteFloat] = Field(default_factory=list)
    boll_lower: list[OptionalFiniteFloat] = Field(default_factory=list)
    atr14_percent: list[OptionalFiniteFloat] = Field(default_factory=list)

class AnalysisResult(BaseModel):
    metrics: PerformanceMetrics
    diagnostics: Diagnostics
    series: AnalysisSeries = Field(default_factory=AnalysisSeries)

class BacktestRequest(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    code: str
    start: date | None = None
    end: date | None = None
    fast_window: PositiveWindow = 20
    slow_window: PositiveWindow = 60
    fee_rate: FeeRate = 0.0001
    slippage_rate: SlippageRate = 0.001
    initial_cash: PositiveFiniteFloat = 100000.0

    @model_validator(mode="after")
    def validate_parameter_relationships(self):
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be less than slow_window")
        if self.start is not None and self.end is not None and self.start > self.end:
            raise ValueError("start must be on or before end")
        return self

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
