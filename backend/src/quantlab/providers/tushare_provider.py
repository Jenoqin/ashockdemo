from datetime import date, datetime, timezone
import pandas as pd
from quantlab.models import Instrument, PriceBar
from quantlab.providers.base import MarketDataProvider, ProviderError

class TushareProvider:
    name = "tushare"
    
    def __init__(self, client):
        self.client = client
        
    _KNOWN = {
        "512480.SH": ("半导体ETF", "etf", "SH"),
        "510300.SH": ("沪深300ETF", "etf", "SH"),
        "510050.SH": ("上证50ETF", "etf", "SH"),
        "510500.SH": ("中证500ETF", "etf", "SH"),
        "588000.SH": ("科创50ETF", "etf", "SH"),
        "159915.SZ": ("创业板ETF", "etf", "SZ"),
        "600519.SH": ("贵州茅台", "equity", "SH"),
        "000001.SZ": ("平安银行", "equity", "SZ"),
        "000858.SZ": ("五粮液", "equity", "SZ"),
        "300750.SZ": ("宁德时代", "equity", "SZ"),
        "601318.SH": ("中国平安", "equity", "SH"),
    }

    def search(self, query: str) -> list[Instrument]:
        q = query.strip().upper()
        results = []
        for code, (name, asset_type, exchange) in self._KNOWN.items():
            if q in code or q in name:
                results.append(Instrument(code=code, name=name, asset_type=asset_type, exchange=exchange))
        return results

    def get_instrument(self, code: str) -> Instrument:
        from quantlab.providers.base import normalize_code
        norm = normalize_code(code)
        if norm in self._KNOWN:
            name, asset_type, exchange = self._KNOWN[norm]
            return Instrument(code=norm, name=name, asset_type=asset_type, exchange=exchange)
        digits, exchange = norm.split(".")
        asset_type = "etf" if digits.startswith(("5", "1")) else "equity"
        name = f"{digits}{' ETF' if asset_type == 'etf' else ''}"
        return Instrument(code=norm, name=name, asset_type=asset_type, exchange=exchange)
        
    def get_daily(self, code: str, start: date, end: date) -> list[PriceBar]:
        digits, _ = code.split(".")
        start_date = start.strftime("%Y%m%d")
        end_date = end.strftime("%Y%m%d")
        try:
            if digits.startswith(("5", "1")):
                df = self.client.fund_daily(ts_code=code, start_date=start_date, end_date=end_date)
            else:
                df = self.client.daily(ts_code=code, start_date=start_date, end_date=end_date)
        except Exception as e:
            raise ProviderError(self.name, code, str(e))
            
        if df is None or df.empty:
            return []
            
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date")
        df = df.drop_duplicates("trade_date", keep="last")
        
        fetched = datetime.now(timezone.utc)
        bars = []
        for _, row in df.iterrows():
            bars.append(PriceBar(
                code=code,
                trade_date=row["trade_date"].date(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["vol"]),
                amount=float(row["amount"]) if "amount" in row else None,
                source=self.name,
                fetched_at=fetched
            ))
        return bars
