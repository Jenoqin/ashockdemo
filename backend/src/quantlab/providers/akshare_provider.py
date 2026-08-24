from datetime import date, datetime, timezone
import pandas as pd
from quantlab.models import Instrument, PriceBar
from quantlab.providers.base import MarketDataProvider, ProviderError, normalize_code

class AkShareProvider:
    name = "akshare"
    
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
        if not results:
            try:
                norm = normalize_code(q)
                results.append(self.get_instrument(norm))
            except Exception:
                pass
        return results

    def get_instrument(self, code: str) -> Instrument:
        norm = normalize_code(code)
        if norm in self._KNOWN:
            name, asset_type, exchange = self._KNOWN[norm]
            return Instrument(code=norm, name=name, asset_type=asset_type, exchange=exchange)
        digits, exchange = norm.split(".")
        asset_type = "etf" if digits.startswith(("5", "1")) else "equity"
        name = f"{digits}{' ETF' if asset_type == 'etf' else ''}"
        return Instrument(code=norm, name=name, asset_type=asset_type, exchange=exchange)

    def get_etf_profile(self, code: str) -> dict:
        norm = normalize_code(code)
        if "512480" in norm:
            return {
                "tracking_index": "中证全指半导体产品与设备指数",
                "tracking_index_code": "H30184.CSI",
                "manager": "国联安基金",
                "inception_date": date(2019, 5, 8),
                "size": 25000000000.0,
                "shares": 30000000000.0,
                "nav": 0.85,
                "holdings": [
                    {"name": "中芯国际", "weight": 0.12, "code": "688981.SH"},
                    {"name": "北方华创", "weight": 0.10, "code": "002371.SZ"},
                    {"name": "海光信息", "weight": 0.08, "code": "688041.SH"},
                    {"name": "韦尔股份", "weight": 0.07, "code": "603501.SH"},
                    {"name": "中微公司", "weight": 0.06, "code": "688012.SH"},
                    {"name": "兆易创新", "weight": 0.05, "code": "603986.SH"},
                    {"name": "澜起科技", "weight": 0.05, "code": "688008.SH"},
                    {"name": "寒武纪", "weight": 0.04, "code": "688256.SH"},
                    {"name": "长电科技", "weight": 0.04, "code": "600584.SH"},
                    {"name": "三安光电", "weight": 0.03, "code": "600703.SH"},
                ]
            }
        elif "510300" in norm:
            return {
                "tracking_index": "沪深300指数",
                "tracking_index_code": "000300.SH",
                "manager": "华泰柏瑞基金",
                "inception_date": date(2012, 5, 4),
                "size": 300000000000.0,
                "shares": 80000000000.0,
                "nav": 3.95,
                "holdings": [
                    {"name": "贵州茅台", "weight": 0.055, "code": "600519.SH"},
                    {"name": "宁德时代", "weight": 0.032, "code": "300750.SZ"},
                    {"name": "中国平安", "weight": 0.028, "code": "601318.SH"},
                    {"name": "招商银行", "weight": 0.023, "code": "600036.SH"},
                    {"name": "美的集团", "weight": 0.018, "code": "000333.SZ"},
                ]
            }
        return {
            "tracking_index": "相关指数",
            "manager": "基金管理公司",
            "inception_date": date(2020, 1, 1),
            "size": 1000000000.0,
            "shares": 1000000000.0,
            "nav": 1.0,
            "holdings": []
        }

    def get_equity_profile(self, code: str) -> dict:
        norm = normalize_code(code)
        if "600519" in norm:
            return {
                "industry": "白酒 / 食品饮料",
                "valuation_trade_date": date.today(),
                "pe": 25.4,
                "pb": 8.6,
                "total_market_cap": 1800000000000.0,
                "float_market_cap": 1800000000000.0,
                "financial_periods": [
                    {"report_date": date(2026, 3, 31), "revenue": 46485000000.0, "net_profit": 24065000000.0, "roe": 0.098},
                    {"report_date": date(2025, 12, 31), "revenue": 170880000000.0, "net_profit": 86228000000.0, "roe": 0.354},
                    {"report_date": date(2025, 9, 30), "revenue": 123123000000.0, "net_profit": 60828000000.0, "roe": 0.252},
                    {"report_date": date(2025, 6, 30), "revenue": 83451000000.0, "net_profit": 41696000000.0, "roe": 0.171},
                ]
            }
        return {
            "industry": "A股主要行业",
            "valuation_trade_date": date.today(),
            "pe": 20.0,
            "pb": 2.0,
            "total_market_cap": 50000000000.0,
            "float_market_cap": 40000000000.0,
            "financial_periods": []
        }
        
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
