from datetime import date, datetime, timezone
import pandas as pd
from quantlab.models import Instrument, PriceBar
from quantlab.providers.base import MarketDataProvider, ProviderError

class AkShareProvider:
    name = "akshare"
    
    def __init__(self, client):
        self.client = client
        
    def search(self, query: str) -> list[Instrument]:
        raise NotImplementedError
        
    def get_instrument(self, code: str) -> Instrument:
        raise NotImplementedError
        
    def get_daily(self, code: str, start: date, end: date) -> list[PriceBar]:
        digits, _ = code.split(".")
        try:
            if digits.startswith(("5", "1")):
                df = self.client.fund_etf_hist_em(
                    symbol=digits, 
                    period="daily", 
                    start_date=start.strftime("%Y%m%d"), 
                    end_date=end.strftime("%Y%m%d"), 
                    adjust="qfq"
                )
            else:
                df = self.client.stock_zh_a_hist(
                    symbol=digits, 
                    period="daily", 
                    start_date=start.strftime("%Y%m%d"), 
                    end_date=end.strftime("%Y%m%d"), 
                    adjust="qfq"
                )
        except Exception as e:
            raise ProviderError(self.name, code, str(e))
            
        if df is None or df.empty:
            return []
            
        df["日期"] = pd.to_datetime(df["日期"])
        df = df.sort_values("日期")
        df = df.drop_duplicates("日期", keep="last")
        
        fetched = datetime.now(timezone.utc)
        bars = []
        for _, row in df.iterrows():
            bars.append(PriceBar(
                code=code,
                trade_date=row["日期"].date(),
                open=float(row["开盘"]),
                high=float(row["最高"]),
                low=float(row["最低"]),
                close=float(row["收盘"]),
                volume=float(row["成交量"]),
                amount=float(row["成交额"]) if "成交额" in row else None,
                source=self.name,
                fetched_at=fetched
            ))
        return bars
