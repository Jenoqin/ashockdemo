from datetime import date
from typing import Protocol
from quantlab.models import Instrument, PriceBar

class ProviderError(RuntimeError):
    def __init__(self, provider: str, code: str, reason: str):
        self.provider = provider
        self.code = code
        self.reason = reason
        super().__init__(f"{provider}:{code}:{reason}")

class MarketDataProvider(Protocol):
    name: str
    def search(self, query: str) -> list[Instrument]:
        raise NotImplementedError
    def get_instrument(self, code: str) -> Instrument:
        raise NotImplementedError
    def get_trade_calendar(
        self, exchange: str, start: date, end: date
    ) -> dict[date, bool]:
        raise NotImplementedError
    def get_listing_date(self, code: str) -> date | None:
        raise NotImplementedError
    def get_daily(self, code: str, start: date, end: date) -> list[PriceBar]:
        raise NotImplementedError
    def get_index_daily(self, code: str, start: date, end: date) -> list[PriceBar]:
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


def normalize_index_code(raw: str) -> str:
    """Normalize an explicit Tushare index code without treating it as a security."""
    value = raw.strip().upper()
    if "." not in value:
        raise ValueError("指数代码必须包含市场后缀")
    symbol, exchange = value.rsplit(".", maxsplit=1)
    if (
        not symbol
        or not symbol.replace("-", "").isalnum()
        or exchange not in {"SH", "SZ", "CSI", "CNI", "SW"}
    ):
        raise ValueError("指数代码格式无效")
    return f"{symbol}.{exchange}"
