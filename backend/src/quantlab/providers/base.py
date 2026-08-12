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
