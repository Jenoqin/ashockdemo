from typing import List
from quantlab.models import PriceBar

def validate_bars(bars: List[PriceBar]) -> List[str]:
    warnings = []
    seen_dates = set()
    
    last_date = None
    for bar in bars:
        date_str = bar.trade_date.isoformat()
        
        if bar.trade_date in seen_dates:
            warnings.append(f"DUPLICATE_TRADE_DATE:{date_str}")
        seen_dates.add(bar.trade_date)
        
        if last_date is not None and bar.trade_date < last_date:
            warnings.append(f"UNSORTED_DATES:{date_str}")
            
        last_date = bar.trade_date
        
        if bar.high < bar.low or bar.open < 0 or bar.high < 0 or bar.low < 0 or bar.close < 0:
            warnings.append(f"INVALID_OHLC:{date_str}")
        elif not (bar.low - 1e-5 <= bar.close <= bar.high + 1e-5):
            warnings.append(f"INVALID_OHLC:{date_str}")
            
        if bar.volume < 0:
            warnings.append(f"NEGATIVE_VOLUME:{date_str}")
            
    return warnings
