from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import sqlite3
from threading import Lock
from time import monotonic
from typing import Any

import pandas as pd

from quantlab.errors import InstrumentNotFoundError
from quantlab.models import Instrument, PriceBar
from quantlab.providers.base import ProviderError, normalize_code


def _value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _float(value: Any, multiplier: float = 1.0) -> float | None:
    value = _value(value)
    if value is None:
        return None
    try:
        return float(value) * multiplier
    except (TypeError, ValueError):
        return None


def _ratio(value: Any) -> float | None:
    number = _float(value)
    return number / 100 if number is not None else None


def _iso_date(value: Any) -> date | None:
    value = _value(value)
    if value is None:
        return None
    try:
        return pd.to_datetime(str(value)).date()
    except (TypeError, ValueError):
        return None


def _json_value(value: Any) -> str | int | float | bool | None:
    value = _value(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        scalar = value.item()
        if scalar is None or isinstance(scalar, (str, int, float, bool)):
            return scalar
    return str(value)


class TushareProvider:
    name = "Tushare Pro"
    catalog_ttl_seconds = 24 * 60 * 60
    stale_catalog_retry_seconds = 60

    def __init__(self, client, cache=None):
        self.client = client
        self.cache = cache
        self._catalog: dict[str, Instrument] = {}
        self._stock_rows: dict[str, dict[str, Any]] = {}
        self._etf_rows: dict[str, dict[str, Any]] = {}
        self._catalog_loaded_at = 0.0
        self._catalog_expires_at = 0.0
        self._catalog_fetched_at: datetime | None = None
        self._catalog_cache_hit = False
        self._catalog_warnings: list[str] = []
        self._lock = Lock()

    @staticmethod
    def _catalog_age_seconds(fetched_at: datetime) -> float:
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - fetched_at).total_seconds())

    def _hydrate_catalog(
        self,
        entries: list[tuple[Instrument, dict]],
        fetched_at: datetime,
        *,
        cache_hit: bool,
        warnings: list[str] | None = None,
        ttl_seconds: float | None = None,
    ) -> dict[str, Instrument]:
        self._catalog = {instrument.code: instrument for instrument, _ in entries}
        self._stock_rows = {
            instrument.code: metadata
            for instrument, metadata in entries
            if instrument.asset_type == "equity"
        }
        self._etf_rows = {
            instrument.code: metadata
            for instrument, metadata in entries
            if instrument.asset_type == "etf"
        }
        now = monotonic()
        self._catalog_loaded_at = now
        self._catalog_expires_at = now + (
            self.catalog_ttl_seconds if ttl_seconds is None else ttl_seconds
        )
        self._catalog_fetched_at = fetched_at
        self._catalog_cache_hit = cache_hit
        self._catalog_warnings = list(warnings or [])
        return self._catalog

    def catalog_meta(self) -> dict[str, Any]:
        return {
            "sources": [self.name],
            "fetched_at": self._catalog_fetched_at or datetime.now(timezone.utc),
            "cache_hit": self._catalog_cache_hit,
            "warnings": list(self._catalog_warnings),
        }

    def _require_client(self, code: str) -> None:
        if self.client is None:
            raise ProviderError(
                self.name,
                code,
                "未配置 TUSHARE_TOKEN 或有效的 TUSHARE_TOKEN_FILE",
            )

    def _load_catalog(self) -> dict[str, Instrument]:
        if self._catalog and monotonic() < self._catalog_expires_at:
            self._catalog_cache_hit = True
            return self._catalog
        with self._lock:
            if self._catalog and monotonic() < self._catalog_expires_at:
                self._catalog_cache_hit = True
                return self._catalog

            cached = self.cache.get_instrument_catalog(self.name) if self.cache else None
            if cached:
                cached_entries, cached_at = cached
                remaining_ttl = self.catalog_ttl_seconds - self._catalog_age_seconds(cached_at)
                if remaining_ttl > 0:
                    return self._hydrate_catalog(
                        cached_entries,
                        cached_at,
                        cache_hit=True,
                        ttl_seconds=remaining_ttl,
                    )

            try:
                self._require_client("catalog")
                stocks = self.client.stock_basic(
                    exchange="", list_status="L",
                    fields="ts_code,symbol,name,fullname,area,industry,list_date",
                )
                etfs = self.client.etf_basic(
                    fields="ts_code,csname,extname,index_code,index_name,mgr,list_date",
                )
            except Exception as exc:
                if cached:
                    return self._hydrate_catalog(
                        cached[0],
                        cached[1],
                        cache_hit=True,
                        warnings=["STALE_CACHE"],
                        ttl_seconds=self.stale_catalog_retry_seconds,
                    )
                if isinstance(exc, ProviderError):
                    raise
                raise ProviderError(self.name, "catalog", str(exc)) from exc

            catalog: dict[str, Instrument] = {}
            stock_rows: dict[str, dict[str, Any]] = {}
            etf_rows: dict[str, dict[str, Any]] = {}
            if stocks is not None:
                for _, row in stocks.iterrows():
                    code = str(row.get("ts_code", "")).upper()
                    name = _value(row.get("name"))
                    if code and name:
                        try:
                            norm = normalize_code(code)
                        except ValueError:
                            continue
                        full_name = _value(row.get("fullname"))
                        catalog[norm] = Instrument(
                            code=norm,
                            name=str(name),
                            full_name=str(full_name) if full_name else None,
                            asset_type="equity",
                            exchange=norm.split(".")[1],
                        )
                        stock_rows[norm] = {
                            key: _json_value(row.get(key))
                            for key in ("industry", "list_date")
                        }
            if etfs is not None:
                for _, row in etfs.iterrows():
                    code = str(row.get("ts_code", "")).upper()
                    name = _value(row.get("csname")) or _value(row.get("extname")) or _value(row.get("cname")) or _value(row.get("name"))
                    if code and name:
                        try:
                            norm = normalize_code(code)
                        except ValueError:
                            continue
                        catalog[norm] = Instrument(code=norm, name=str(name), asset_type="etf", exchange=norm.split(".")[1])
                        etf_rows[norm] = {
                            key: _json_value(row.get(key))
                            for key in ("index_name", "index_code", "mgr", "list_date")
                        }
            if not catalog:
                if cached:
                    return self._hydrate_catalog(
                        cached[0],
                        cached[1],
                        cache_hit=True,
                        warnings=["STALE_CACHE"],
                        ttl_seconds=self.stale_catalog_retry_seconds,
                    )
                raise ProviderError(self.name, "catalog", "证券主数据为空")
            fetched_at = datetime.now(timezone.utc)
            entries = [
                (
                    instrument,
                    stock_rows.get(code) or etf_rows.get(code) or {},
                )
                for code, instrument in catalog.items()
            ]
            warnings: list[str] = []
            if self.cache:
                try:
                    self.cache.replace_instrument_catalog(
                        self.name, entries, fetched_at
                    )
                except (sqlite3.Error, ValueError):
                    warnings.append("CACHE_WRITE_FAILED")
            return self._hydrate_catalog(
                entries,
                fetched_at,
                cache_hit=False,
                warnings=warnings,
            )

    def search(self, query: str) -> list[Instrument]:
        text = query.strip().upper()
        if not text:
            return []
        catalog = self._load_catalog()
        exact_code = None
        try:
            exact_code = normalize_code(text)
        except ValueError:
            pass
        matches = [
            item for item in catalog.values()
            if text in item.code
            or text in item.name.upper()
            or text in (item.full_name or "").upper()
        ]
        matches.sort(key=lambda item: (item.code != exact_code, not item.name.upper().startswith(text), item.code))
        return matches[:20]

    def get_instrument(self, code: str) -> Instrument:
        norm = normalize_code(code)
        instrument = self._load_catalog().get(norm)
        if instrument is None:
            raise InstrumentNotFoundError(norm)
        return instrument

    def get_trade_calendar(
        self, exchange: str, start: date, end: date
    ) -> dict[date, bool]:
        self._require_client(f"calendar:{exchange}")
        if exchange not in {"SSE", "SZSE"}:
            raise ProviderError(self.name, exchange, "不支持的交易所日历")
        try:
            frame = self.client.trade_cal(
                exchange=exchange,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                fields="exchange,cal_date,is_open",
            )
        except Exception as exc:
            raise ProviderError(self.name, exchange, str(exc)) from exc
        if frame is None or frame.empty:
            raise ProviderError(self.name, exchange, "交易日历为空")
        required = {"cal_date", "is_open"}
        if not required.issubset(frame.columns):
            raise ProviderError(self.name, exchange, "交易日历字段不完整")
        if "exchange" in frame.columns and any(
            str(value).upper() != exchange for value in frame["exchange"]
        ):
            raise ProviderError(self.name, exchange, "交易日历包含错误交易所")
        parsed = pd.to_datetime(frame["cal_date"].astype(str), errors="coerce")
        if parsed.isna().any():
            raise ProviderError(self.name, exchange, "交易日历日期无效")
        days = [value.date() for value in parsed]
        if len(days) != len(set(days)):
            raise ProviderError(self.name, exchange, "交易日历包含重复日期")
        if any(day < start or day > end for day in days):
            raise ProviderError(self.name, exchange, "交易日历包含区间外日期")
        expected = {
            start + timedelta(days=offset)
            for offset in range((end - start).days + 1)
        }
        if set(days) != expected:
            raise ProviderError(self.name, exchange, "交易日历日期不完整")
        statuses: list[bool] = []
        for value in frame["is_open"]:
            if _value(value) not in (0, 1, "0", "1"):
                raise ProviderError(self.name, exchange, "交易日历状态无效")
            statuses.append(bool(int(value)))
        return dict(zip(days, statuses, strict=True))

    def get_listing_date(self, code: str) -> date | None:
        norm = normalize_code(code)
        self._load_catalog()
        row = self._stock_rows.get(norm) or self._etf_rows.get(norm)
        if row is None:
            raise ProviderError(self.name, norm, "证券不在基础信息目录中")
        return _iso_date(row.get("list_date"))

    def get_equity_profile(self, code: str) -> dict[str, Any]:
        norm = normalize_code(code)
        self._load_catalog()
        stock = self._stock_rows.get(norm)
        if stock is None:
            raise InstrumentNotFoundError(norm)
        try:
            basic = self.client.daily_basic(
                ts_code=norm,
                fields="ts_code,trade_date,turnover_rate,pe,pb,total_mv,circ_mv",
            )
            income = self.client.income(
                ts_code=norm,
                fields="ann_date,end_date,report_type,total_revenue,revenue,n_income,n_income_attr_p",
            )
            indicators = self.client.fina_indicator(
                ts_code=norm,
                fields="ann_date,end_date,roe,netprofit_yoy,tr_yoy,or_yoy,grossprofit_margin,netprofit_margin,debt_to_assets",
            )
        except Exception as exc:
            raise ProviderError(self.name, norm, str(exc)) from exc

        basic_row = basic.sort_values("trade_date", ascending=False).iloc[0].to_dict() if basic is not None and not basic.empty else {}
        indicator_rows: dict[str, dict[str, Any]] = {}
        if indicators is not None and not indicators.empty:
            indicators = indicators.sort_values(["end_date", "ann_date"], ascending=False).drop_duplicates("end_date")
            indicator_rows = {str(row["end_date"]): row.to_dict() for _, row in indicators.iterrows()}

        periods = []
        if income is not None and not income.empty:
            income = income.sort_values(["end_date", "ann_date"], ascending=False).drop_duplicates("end_date")
            for _, row in income.head(4).iterrows():
                end_date = str(row["end_date"])
                indicator = indicator_rows.get(end_date, {})
                periods.append({
                    "report_date": _iso_date(end_date),
                    "revenue": _float(_value(row.get("total_revenue")) or _value(row.get("revenue"))),
                    "revenue_yoy": _ratio(_value(indicator.get("tr_yoy")) or _value(indicator.get("or_yoy"))),
                    "net_profit": _float(_value(row.get("n_income_attr_p")) or _value(row.get("n_income"))),
                    "net_profit_yoy": _ratio(indicator.get("netprofit_yoy")),
                    "roe": _ratio(indicator.get("roe")),
                    "gross_margin": _ratio(indicator.get("grossprofit_margin")),
                    "net_margin": _ratio(indicator.get("netprofit_margin")),
                    "debt_ratio": _ratio(indicator.get("debt_to_assets")),
                })

        return {
            "industry": _value(stock.get("industry")),
            "valuation_trade_date": _iso_date(basic_row.get("trade_date")),
            "pe": _float(basic_row.get("pe")),
            "pb": _float(basic_row.get("pb")),
            # Tushare daily_basic documents market value in 10,000 CNY.
            "total_market_cap": _float(basic_row.get("total_mv"), 1e4),
            "float_market_cap": _float(basic_row.get("circ_mv"), 1e4),
            "turnover_rate": _ratio(basic_row.get("turnover_rate")),
            "financial_periods": [period for period in periods if period["report_date"] is not None],
        }

    def get_etf_profile(self, code: str) -> dict[str, Any]:
        norm = normalize_code(code)
        self._load_catalog()
        etf = self._etf_rows.get(norm)
        if etf is None:
            raise InstrumentNotFoundError(norm)
        try:
            fund = self.client.fund_basic(
                ts_code=norm,
                fields="ts_code,name,management,found_date,list_date,benchmark",
            )
            nav = self.client.fund_nav(
                ts_code=norm,
                fields="ts_code,nav_date,unit_nav,net_asset,total_netasset",
            )
            holdings = self.client.fund_portfolio(
                ts_code=norm,
                fields="ts_code,ann_date,end_date,symbol,mkv,amount,stk_mkv_ratio",
            )
        except Exception as exc:
            raise ProviderError(self.name, norm, str(exc)) from exc

        fund_row = fund.iloc[0].to_dict() if fund is not None and not fund.empty else {}
        nav_row = nav.sort_values("nav_date", ascending=False).iloc[0].to_dict() if nav is not None and not nav.empty else {}
        holding_list = []
        if holdings is not None and not holdings.empty:
            holdings = holdings.sort_values(["end_date", "stk_mkv_ratio"], ascending=False)
            latest_period = holdings.iloc[0]["end_date"]
            for _, row in holdings[holdings["end_date"] == latest_period].head(10).iterrows():
                symbol = str(row.get("symbol", "")).strip()
                try:
                    holding_code = normalize_code(symbol)
                except ValueError:
                    holding_code = None
                holding = self._catalog.get(holding_code) if holding_code else None
                holding_list.append({
                    "code": holding_code,
                    "name": holding.name if holding else symbol or "未披露名称",
                    "weight": _ratio(row.get("stk_mkv_ratio")) or 0,
                })

        return {
            "tracking_index": _value(etf.get("index_name")) or _value(fund_row.get("benchmark")),
            "tracking_index_code": _value(etf.get("index_code")),
            "manager": _value(etf.get("mgr")) or _value(fund_row.get("management")),
            "inception_date": _iso_date(fund_row.get("found_date")) or _iso_date(etf.get("list_date")),
            "size": _float(_value(nav_row.get("total_netasset")) or _value(nav_row.get("net_asset"))),
            "nav": _float(nav_row.get("unit_nav")),
            "holdings": holding_list,
        }

    def get_suspension_dates(
        self, code: str, start: date, end: date
    ) -> set[date]:
        norm = normalize_code(code)
        self._require_client(norm)
        try:
            frame = self.client.suspend_d(
                ts_code=norm,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                fields="ts_code,trade_date,suspend_type",
            )
        except Exception as exc:
            raise ProviderError(self.name, norm, str(exc)) from exc
        if frame is None or frame.empty:
            return set()
        if not {"ts_code", "trade_date"}.issubset(frame.columns):
            raise ProviderError(self.name, norm, "停复牌响应字段不完整")
        if any(str(value).upper() != norm for value in frame["ts_code"]):
            raise ProviderError(self.name, norm, "停复牌响应包含错误代码")
        parsed = pd.to_datetime(frame["trade_date"].astype(str), errors="coerce")
        if parsed.isna().any():
            raise ProviderError(self.name, norm, "停复牌响应日期无效")
        days = {value.date() for value in parsed}
        if any(day < start or day > end for day in days):
            raise ProviderError(self.name, norm, "停复牌响应包含区间外日期")
        return days

    def get_daily(self, code: str, start: date, end: date) -> list[PriceBar]:
        norm = normalize_code(code)
        self._require_client(norm)
        digits = norm.split(".")[0]
        start_date = start.strftime("%Y%m%d")
        end_date = end.strftime("%Y%m%d")
        try:
            if digits.startswith(("5", "1")):
                frame = self.client.fund_daily(ts_code=norm, start_date=start_date, end_date=end_date)
                factors = self.client.fund_adj(ts_code=norm, start_date=start_date, end_date=end_date)
            else:
                frame = self.client.daily(ts_code=norm, start_date=start_date, end_date=end_date)
                factors = self.client.adj_factor(ts_code=norm, start_date=start_date, end_date=end_date)
        except Exception as exc:
            raise ProviderError(self.name, norm, str(exc)) from exc
        if frame is None or frame.empty:
            return []
        if factors is None or factors.empty:
            raise ProviderError(self.name, norm, "复权因子为空")
        required = {
            "ts_code", "trade_date", "open", "high", "low", "close", "vol"
        }
        if not required.issubset(frame.columns):
            raise ProviderError(self.name, norm, "行情响应字段不完整")
        if not {"trade_date", "adj_factor"}.issubset(factors.columns):
            raise ProviderError(self.name, norm, "复权因子字段不完整")
        if any(str(value).upper() != norm for value in frame["ts_code"]):
            raise ProviderError(self.name, norm, "行情响应包含错误代码")

        raw_dates = frame["trade_date"].astype(str)
        parsed_dates = pd.to_datetime(raw_dates, errors="coerce")
        if parsed_dates.isna().any():
            raise ProviderError(self.name, norm, "行情响应日期无效")
        days = [value.date() for value in parsed_dates]
        if len(days) != len(set(days)):
            raise ProviderError(self.name, norm, "行情响应包含重复日期")
        if any(day < start or day > end for day in days):
            raise ProviderError(self.name, norm, "行情响应包含区间外日期")

        factor_dates = factors["trade_date"].astype(str)
        parsed_factor_dates = pd.to_datetime(factor_dates, errors="coerce")
        if parsed_factor_dates.isna().any():
            raise ProviderError(self.name, norm, "复权因子日期无效")
        factor_days = [value.date() for value in parsed_factor_dates]
        if len(factor_days) != len(set(factor_days)):
            raise ProviderError(self.name, norm, "复权因子包含重复日期")
        if any(day < start or day > end for day in factor_days):
            raise ProviderError(self.name, norm, "复权因子包含区间外日期")
        if "ts_code" in factors.columns and any(
            str(value).upper() != norm for value in factors["ts_code"]
        ):
            raise ProviderError(self.name, norm, "复权因子包含错误代码")
        try:
            frame = frame.merge(
                factors[["trade_date", "adj_factor"]],
                on="trade_date",
                how="left",
                validate="one_to_one",
            )
            if frame["adj_factor"].isna().any():
                raise ProviderError(self.name, norm, "复权因子不完整")
            for column in ("open", "high", "low", "close"):
                frame[column] = (
                    frame[column].astype(float) * frame["adj_factor"].astype(float)
                )
            frame["trade_date"] = parsed_dates
            frame = frame.sort_values("trade_date")
            fetched = datetime.now(timezone.utc)
            return [
                PriceBar(
                    code=norm,
                    trade_date=row["trade_date"].date(),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["vol"]),
                    amount=_float(row.get("amount"), 1e3),
                    source=self.name,
                    fetched_at=fetched,
                )
                for _, row in frame.iterrows()
            ]
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(self.name, norm, f"行情响应无效: {exc}") from exc
