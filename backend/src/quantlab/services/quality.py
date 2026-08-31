import math
from typing import List
from quantlab.models import PriceBar


def _is_finite(value: object) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def validate_bars(bars: List[PriceBar]) -> List[str]:
    warnings = []
    seen_dates = set()
    seen_codes = set()
    seen_sources = set()
    
    last_date = None
    last_close = None
    for bar in bars:
        date_str = bar.trade_date.isoformat()
        seen_codes.add(bar.code)
        seen_sources.add(bar.source)
        
        if bar.trade_date in seen_dates:
            warnings.append(f"DUPLICATE_TRADE_DATE:{date_str}")
        seen_dates.add(bar.trade_date)
        
        if last_date is not None and bar.trade_date < last_date:
            warnings.append(f"UNSORTED_DATES:{date_str}")
            
        last_date = bar.trade_date
        
        price_values = (bar.open, bar.high, bar.low, bar.close)
        prices_are_finite = all(_is_finite(value) for value in price_values)
        if not prices_are_finite:
            warnings.append(f"NON_FINITE_NUMERIC:{date_str}:price")
        elif bar.high < bar.low or bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0:
            warnings.append(f"INVALID_OHLC:{date_str}")
        elif not (
            bar.low - 1e-5 <= bar.open <= bar.high + 1e-5
            and bar.low - 1e-5 <= bar.close <= bar.high + 1e-5
        ):
            warnings.append(f"INVALID_OHLC:{date_str}")

        if prices_are_finite and last_close is not None and last_close > 0:
            daily_return = bar.close / last_close - 1
            if not _is_finite(daily_return):
                warnings.append(f"NON_FINITE_NUMERIC:{date_str}:daily_return")
            elif abs(daily_return) > 0.5:
                warnings.append(f"EXTREME_DAILY_RETURN:{date_str}:{daily_return:.6f}")
        last_close = bar.close if prices_are_finite else None
            
        if not _is_finite(bar.volume):
            warnings.append(f"NON_FINITE_NUMERIC:{date_str}:volume")
        elif bar.volume < 0:
            warnings.append(f"NEGATIVE_VOLUME:{date_str}")

        if bar.amount is not None:
            if not _is_finite(bar.amount):
                warnings.append(f"NON_FINITE_NUMERIC:{date_str}:amount")
            elif bar.amount < 0:
                warnings.append(f"INVALID_AMOUNT:{date_str}")

    if len(seen_codes) > 1:
        warnings.append("MIXED_CODES")
    if len(seen_sources) > 1:
        warnings.append("MIXED_SOURCES")

    return warnings
