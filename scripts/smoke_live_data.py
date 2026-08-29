"""Optional live completeness smoke test for the Tushare cache."""

from datetime import date, timedelta
from pathlib import Path
import sys

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from quantlab.api.dependencies import get_market_data_service  # noqa: E402


def frame_dates(frame) -> set[date]:
    if frame is None or frame.empty:
        return set()
    return set(pd.to_datetime(frame["trade_date"].astype(str)).dt.date)


def main() -> None:
    code = "512480.SH"
    end = date.today()
    start = end - timedelta(days=365)
    service = get_market_data_service()
    provider = service.provider

    if provider.client is None:
        raise RuntimeError("未配置 TUSHARE_TOKEN，无法运行真实数据 smoke test")

    calendar = provider.get_trade_calendar("SSE", start, end)
    expected = {day for day, is_open in calendar.items() if is_open}
    params = {
        "ts_code": code,
        "start_date": start.strftime("%Y%m%d"),
        "end_date": end.strftime("%Y%m%d"),
    }
    daily_dates = frame_dates(provider.client.fund_daily(**params))
    factor_dates = frame_dates(provider.client.fund_adj(**params))
    cached_dates = {
        bar.trade_date for bar in service.get_daily(code, start, end).bars
    }

    counts = {
        "trade_cal_open": len(expected),
        "fund_daily": len(daily_dates),
        "fund_adj": len(factor_dates),
        "verified_cache": len(cached_dates),
    }
    print(counts)
    if not (expected == daily_dates == factor_dates == cached_dates):
        raise RuntimeError({
            "calendar_vs_daily": sorted(expected ^ daily_dates),
            "daily_vs_factor": sorted(daily_dates ^ factor_dates),
            "daily_vs_cache": sorted(daily_dates ^ cached_dates),
        })
    print("Tushare completeness smoke test passed")


if __name__ == "__main__":
    main()
