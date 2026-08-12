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
