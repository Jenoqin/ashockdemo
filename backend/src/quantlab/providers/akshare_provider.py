from __future__ import annotations

from datetime import date, datetime, timezone
import math
import re
from threading import Lock
from time import monotonic
from typing import Any

import pandas as pd

from quantlab.errors import InstrumentNotFoundError
from quantlab.models import Instrument, PriceBar
from quantlab.providers.base import ProviderError, normalize_code


def _clean_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        value = value.strip()
        if not value or value in {"-", "--", "None", "nan"}:
            return None
    return value


def _number(value: Any) -> float | None:
    value = _clean_value(value)
    if value is None:
        return None
    if isinstance(value, str):
        value = value.replace(",", "").replace("%", "")
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _money(value: Any) -> float | None:
    value = _clean_value(value)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return _number(value)
    text = str(value).replace(",", "").strip()
    match = re.search(r"(-?\d+(?:\.\d+)?)", text)
    if not match:
        return None
    result = float(match.group(1))
    if "万亿" in text:
        result *= 1e12
    elif "亿" in text:
        result *= 1e8
    elif "万" in text:
        result *= 1e4
    return result


def _date_value(value: Any) -> date | None:
    value = _clean_value(value)
    if value is None:
        return None
    try:
        return pd.to_datetime(str(value)).date()
    except (TypeError, ValueError):
        return None


def _exchange(code: str) -> str:
    return normalize_code(code).split(".")[1]


class AkShareProvider:
    """AkShare adapter that never substitutes synthetic live metadata."""

    name = "AkShare"
    catalog_ttl_seconds = 6 * 60 * 60
    spot_ttl_seconds = 60

    def __init__(self, client):
        self.client = client
        self._catalog: dict[str, Instrument] = {}
        self._catalog_loaded_at = 0.0
        self._stock_spot = pd.DataFrame()
        self._stock_spot_loaded_at = 0.0
        self._lock = Lock()

    def _load_catalog(self) -> dict[str, Instrument]:
        if self._catalog and monotonic() - self._catalog_loaded_at < self.catalog_ttl_seconds:
            return self._catalog
        with self._lock:
            if self._catalog and monotonic() - self._catalog_loaded_at < self.catalog_ttl_seconds:
                return self._catalog
            catalog: dict[str, Instrument] = {}
            errors: list[str] = []
            try:
                stocks = self.client.stock_info_a_code_name()
                for _, row in stocks.iterrows():
                    digits = str(row.get("code", row.get("代码", ""))).strip().zfill(6)
                    name = _clean_value(row.get("name", row.get("名称")))
                    if len(digits) == 6 and digits.isdigit() and name:
                        code = normalize_code(digits)
                        catalog[code] = Instrument(code=code, name=str(name), asset_type="equity", exchange=_exchange(code))
            except Exception as exc:
                errors.append(f"股票列表：{exc}")
            try:
                etfs = self.client.fund_etf_category_sina(symbol="ETF基金")
                for _, row in etfs.iterrows():
                    digits = str(row.get("代码", "")).strip().zfill(6)
                    name = _clean_value(row.get("名称"))
                    if len(digits) == 6 and digits.isdigit() and name:
                        code = normalize_code(digits)
                        catalog[code] = Instrument(code=code, name=str(name), asset_type="etf", exchange=_exchange(code))
            except Exception as exc:
                errors.append(f"ETF 列表：{exc}")
            if not catalog:
                raise ProviderError(self.name, "catalog", "；".join(errors) or "证券列表为空")
            self._catalog = catalog
            self._catalog_loaded_at = monotonic()
            return catalog

    def _get_stock_spot(self) -> pd.DataFrame:
        if not self._stock_spot.empty and monotonic() - self._stock_spot_loaded_at < self.spot_ttl_seconds:
            return self._stock_spot
        frame = self.client.stock_zh_a_spot_em()
        if frame is None or frame.empty:
            raise ProviderError(self.name, "stock-spot", "股票实时行情为空")
        self._stock_spot = frame
        self._stock_spot_loaded_at = monotonic()
        return frame

    def search(self, query: str) -> list[Instrument]:
        value = query.strip().upper()
        if not value:
            return []
        catalog = self._load_catalog()
        exact_code = None
        try:
            exact_code = normalize_code(value)
        except ValueError:
            pass
        matches = [item for item in catalog.values() if value in item.code or value in item.name.upper()]
        matches.sort(key=lambda item: (item.code != exact_code, not item.name.upper().startswith(value), item.code))
        return matches[:20]

    def get_instrument(self, code: str) -> Instrument:
        norm = normalize_code(code)
        instrument = self._load_catalog().get(norm)
        if instrument is None:
            raise InstrumentNotFoundError(norm)
        return instrument

    def get_etf_profile(self, code: str) -> dict[str, Any]:
        norm = normalize_code(code)
        digits = norm.split(".")[0]
        basic: dict[str, Any] = {}
        try:
            frame = self.client.fund_individual_basic_info_xq(symbol=digits)
            if frame is not None and not frame.empty:
                key_col = "item" if "item" in frame else "项目"
                value_col = "value" if "value" in frame else "数据"
                if key_col in frame and value_col in frame:
                    basic = {str(row[key_col]).strip(): _clean_value(row[value_col]) for _, row in frame.iterrows()}
        except Exception:
            basic = {}

        holdings = []
        for year in (str(date.today().year), str(date.today().year - 1)):
            try:
                frame = self.client.fund_portfolio_hold_em(symbol=digits, date=year)
                if frame is None or frame.empty:
                    continue
                for _, row in frame.head(10).iterrows():
                    weight = _number(row.get("占净值比例"))
                    name = _clean_value(row.get("股票名称"))
                    if name and weight is not None:
                        holding_code = _clean_value(row.get("股票代码"))
                        holdings.append({"name": str(name), "weight": min(max(weight / 100, 0), 1), "code": str(holding_code) if holding_code else None})
                if holdings:
                    break
            except Exception:
                continue

        def first(*keys: str) -> Any:
            for key in keys:
                if _clean_value(basic.get(key)) is not None:
                    return basic[key]
            return None

        profile = {
            "tracking_index": first("跟踪标的", "跟踪指数", "业绩比较基准"),
            "manager": first("基金公司", "基金管理人", "管理人"),
            "inception_date": _date_value(first("成立时间", "成立日期")),
            "size": _money(first("最新规模", "基金规模", "资产规模")),
            "holdings": holdings,
        }
        if not any(value not in (None, [], {}) for value in profile.values()):
            raise ProviderError(self.name, norm, "ETF 资料为空")
        return profile

    def get_equity_profile(self, code: str) -> dict[str, Any]:
        norm = normalize_code(code)
        digits = norm.split(".")[0]
        info: dict[str, Any] = {}
        try:
            frame = self.client.stock_individual_info_em(symbol=digits)
            if frame is not None and not frame.empty and {"item", "value"}.issubset(frame.columns):
                info = {str(row["item"]).strip(): _clean_value(row["value"]) for _, row in frame.iterrows()}
        except Exception:
            info = {}

        spot_row: dict[str, Any] = {}
        try:
            spot = self._get_stock_spot()
            rows = spot[spot["代码"].astype(str).str.zfill(6) == digits]
            if not rows.empty:
                spot_row = rows.iloc[0].to_dict()
        except Exception:
            spot_row = {}

        pe = _number(spot_row.get("市盈率-动态", spot_row.get("市盈率")))
        pb = _number(spot_row.get("市净率"))
        profile = {
            "industry": _clean_value(info.get("行业")),
            "valuation_trade_date": date.today() if pe is not None or pb is not None else None,
            "pe": pe,
            "pb": pb,
            "total_market_cap": _number(spot_row.get("总市值")) or _number(info.get("总市值")),
            "float_market_cap": _number(spot_row.get("流通市值")) or _number(info.get("流通市值")),
            "financial_periods": [],
        }
        if not any(value not in (None, [], {}) for value in profile.values()):
            raise ProviderError(self.name, norm, "股票资料为空")
        return profile

    def get_daily(self, code: str, start: date, end: date) -> list[PriceBar]:
        norm = normalize_code(code)
        digits = norm.split(".")[0]
        try:
            # Daily routing must not wait for the slower security catalog. The
            # public API validates instruments separately before research loads.
            if digits.startswith(("5", "1")):
                frame = self.client.fund_etf_hist_em(symbol=digits, period="daily", start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d"), adjust="hfq")
            else:
                frame = self.client.stock_zh_a_hist(symbol=digits, period="daily", start_date=start.strftime("%Y%m%d"), end_date=end.strftime("%Y%m%d"), adjust="hfq")
        except Exception as exc:
            raise ProviderError(self.name, norm, str(exc)) from exc

        if frame is None or frame.empty:
            return []
        frame["日期"] = pd.to_datetime(frame["日期"])
        frame = frame.sort_values("日期").drop_duplicates("日期", keep="last")
        fetched = datetime.now(timezone.utc)
        return [
            PriceBar(
                code=norm, trade_date=row["日期"].date(), open=float(row["开盘"]), high=float(row["最高"]),
                low=float(row["最低"]), close=float(row["收盘"]), volume=float(row["成交量"]),
                amount=float(row["成交额"]) if "成交额" in row and _clean_value(row["成交额"]) is not None else None,
                source=self.name, fetched_at=fetched,
            )
            for _, row in frame.iterrows()
        ]
