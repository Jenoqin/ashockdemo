from datetime import date, datetime, timezone
import pandas as pd
from quantlab.models import Instrument, PriceBar
from quantlab.providers.base import MarketDataProvider, ProviderError

class TushareProvider:
    name = "tushare"
    
    def __init__(self, client):
        self.client = client
        
    def search(self, query: str) -> list[Instrument]:
        raise NotImplementedError
        
    def get_instrument(self, code: str) -> Instrument:
        raise NotImplementedError
        
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
