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
