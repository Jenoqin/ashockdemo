import numpy as np
import pandas as pd
from typing import Tuple, Optional
from quantlab.models import Diagnostics, DiagnosticCategory, ScoreRule, PerformanceMetrics, AnalysisResult

def max_drawdown(series: pd.Series) -> Tuple[float, int]:
    if len(series) == 0:
        return 0.0, 0
    running_max = series.cummax()
    drawdowns = (series - running_max) / running_max
    max_dd = drawdowns.min()
    
    # Calculate duration
    peak_idx = 0
    max_duration = 0
    current_duration = 0
    for val, peak in zip(series, running_max):
        if val >= peak:
            current_duration = 0
        else:
            current_duration += 1
        if current_duration > max_duration:
            max_duration = current_duration
            
    return float(max_dd) if not pd.isna(max_dd) else 0.0, max_duration

def performance_metrics(returns: pd.Series, risk_free_rate: float = 0.02) -> PerformanceMetrics:
    if len(returns.dropna()) == 0:
        return PerformanceMetrics()
        
    ann_ret = (1 + returns.dropna()).prod() ** (252 / len(returns.dropna())) - 1
    ann_vol = returns.std(ddof=1) * np.sqrt(252)
    downside = returns[returns < 0].std(ddof=1) * np.sqrt(252)
    
    sharpe = (ann_ret - risk_free_rate) / ann_vol if ann_vol > 0 else None
    sortino = (ann_ret - risk_free_rate) / downside if downside > 0 else None
    
    return PerformanceMetrics(
        annualized_return=float(ann_ret) if not pd.isna(ann_ret) else None,
        annualized_volatility=float(ann_vol) if not pd.isna(ann_vol) else None,
        downside=float(downside) if not pd.isna(downside) else None,
        sharpe=float(sharpe) if pd.notna(sharpe) else None,
        sortino=float(sortino) if pd.notna(sortino) else None,
    )

def technical_frame(close: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"close": close})
    df["ma5"] = close.rolling(5).mean()
    df["ma10"] = close.rolling(10).mean()
    df["ma20"] = close.rolling(20).mean()
    df["ma60"] = close.rolling(60).mean()
    
    exp12 = close.ewm(span=12, adjust=False).mean()
    exp26 = close.ewm(span=26, adjust=False).mean()
    df["macd"] = exp12 - exp26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]
    
    delta = close.diff()
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    
    alpha = 1 / 14
    roll_up = up.ewm(alpha=alpha, adjust=False).mean()
    roll_down = down.abs().ewm(alpha=alpha, adjust=False).mean()
    rs = roll_up / roll_down
    df["rsi14"] = 100.0 - (100.0 / (1.0 + rs))
    
    df["boll_mid"] = close.rolling(20).mean()
    std20 = close.rolling(20).std(ddof=0)
    df["boll_upper"] = df["boll_mid"] + 2 * std20
    df["boll_lower"] = df["boll_mid"] - 2 * std20
    
    return df

def score_diagnostics(frame: pd.DataFrame) -> Diagnostics:
    if len(frame) == 0:
        empty = DiagnosticCategory(score=0, rules=[])
        return Diagnostics(trend=empty, momentum=empty, volatility=empty, drawdown=empty)
        
    last = frame.iloc[-1]
    
    # Trend
    t_rules = []
    close_above_ma20 = pd.notna(last["close"]) and pd.notna(last["ma20"]) and last["close"] > last["ma20"]
    t_rules.append(ScoreRule(label="Close > MA20", points=30, triggered=bool(close_above_ma20), explanation="Price is above 20-day average"))
    
    ma20_above_ma60 = pd.notna(last["ma20"]) and pd.notna(last["ma60"]) and last["ma20"] > last["ma60"]
    t_rules.append(ScoreRule(label="MA20 > MA60", points=30, triggered=bool(ma20_above_ma60), explanation="Short-term trend above long-term trend"))
    
    if len(frame) >= 5:
        ma20_slope = frame["ma20"].iloc[-1] - frame["ma20"].iloc[-5]
        slope_pos = pd.notna(ma20_slope) and ma20_slope > 0
    else:
        slope_pos = False
    t_rules.append(ScoreRule(label="MA20 Slope > 0", points=20, triggered=bool(slope_pos), explanation="20-day average is rising over last 5 days"))
    
    macd_pos = pd.notna(last["macd_hist"]) and last["macd_hist"] > 0
    t_rules.append(ScoreRule(label="MACD Hist > 0", points=20, triggered=bool(macd_pos), explanation="MACD histogram is positive"))
    
    t_score = sum(r.points for r in t_rules if r.triggered)
    
    # Momentum
    m_rules = []
    rsi_range = pd.notna(last["rsi14"]) and 45 <= last["rsi14"] <= 70
    m_rules.append(ScoreRule(label="RSI in [45, 70]", points=35, triggered=bool(rsi_range), explanation="RSI is in healthy momentum range"))
    
    if len(frame) >= 20:
        ret20 = frame["close"].iloc[-1] / frame["close"].iloc[-20] - 1
        ret20_pos = pd.notna(ret20) and ret20 > 0
    else:
        ret20_pos = False
    m_rules.append(ScoreRule(label="20-day Return > 0", points=35, triggered=bool(ret20_pos), explanation="Positive return over 20 days"))
    
    macd_above_signal = pd.notna(last["macd"]) and pd.notna(last["macd_signal"]) and last["macd"] > last["macd_signal"]
    m_rules.append(ScoreRule(label="MACD > Signal", points=30, triggered=bool(macd_above_signal), explanation="MACD line is above signal line"))
    
    m_score = sum(r.points for r in m_rules if r.triggered)
    
    # Volatility
    returns = frame["close"].pct_change()
    roll_vol20 = returns.rolling(20).std(ddof=1) * np.sqrt(252)
    vol_rules = []
    
    if len(roll_vol20) >= 60:
        vol20_median60 = roll_vol20.rolling(60).median().iloc[-1]
        curr_vol20 = roll_vol20.iloc[-1]
        vol_below_med = pd.notna(curr_vol20) and pd.notna(vol20_median60) and curr_vol20 < vol20_median60
    else:
        vol_below_med = False
    vol_rules.append(ScoreRule(label="Vol < 60d Median", points=60, triggered=bool(vol_below_med), explanation="Current volatility is below 60-day median"))
    
    if len(roll_vol20) >= 6:
        curr_vol20 = roll_vol20.iloc[-1]
        prev_vol20 = roll_vol20.iloc[-6]
        vol_lower = pd.notna(curr_vol20) and pd.notna(prev_vol20) and curr_vol20 < prev_vol20
    else:
        vol_lower = False
    vol_rules.append(ScoreRule(label="Vol Dropping", points=40, triggered=bool(vol_lower), explanation="Volatility is lower than 5 days ago"))
    
    v_score = sum(r.points for r in vol_rules if r.triggered)
    
    # Drawdown
    d_rules = []
    running_max = frame["close"].cummax()
    drawdowns = (frame["close"] - running_max) / running_max
    
    curr_dd = drawdowns.iloc[-1] if len(drawdowns) > 0 else 0
    dd_above_10 = pd.notna(curr_dd) and curr_dd > -0.10
    d_rules.append(ScoreRule(label="Current DD > -10%", points=40, triggered=bool(dd_above_10), explanation="Current drawdown is less than 10%"))
    
    max_dd, max_dur = max_drawdown(frame["close"])
    max_dd_above_20 = max_dd > -0.20
    d_rules.append(ScoreRule(label="Max DD > -20%", points=30, triggered=bool(max_dd_above_20), explanation="Maximum drawdown is less than 20%"))
    
    dur_below_60 = max_dur <= 60
    d_rules.append(ScoreRule(label="Max DD Duration <= 60", points=30, triggered=bool(dur_below_60), explanation="Longest drawdown duration is at most 60 days"))
    
    d_score = sum(r.points for r in d_rules if r.triggered)
    
    return Diagnostics(
        trend=DiagnosticCategory(score=t_score, rules=t_rules),
        momentum=DiagnosticCategory(score=m_score, rules=m_rules),
        volatility=DiagnosticCategory(score=v_score, rules=vol_rules),
        drawdown=DiagnosticCategory(score=d_score, rules=d_rules)
    )

def analyze_market(bars: list, benchmark_bars=None, risk_free_rate: float = 0.02) -> AnalysisResult:
    if not bars:
        return AnalysisResult(metrics=PerformanceMetrics(), diagnostics=score_diagnostics(pd.DataFrame()))
        
    df = pd.DataFrame([b.model_dump() for b in bars])
    metrics = performance_metrics(df["close"].pct_change(), risk_free_rate=risk_free_rate)
    
    if benchmark_bars:
        bench_df = pd.DataFrame([b.model_dump() for b in benchmark_bars])
        # Inner join returns by trade date
        asset_ret = df.set_index("trade_date")["close"].pct_change()
        bench_ret = bench_df.set_index("trade_date")["close"].pct_change()
        overlap = pd.concat([asset_ret, bench_ret], axis=1, join="inner", keys=["asset", "bench"]).dropna()
        if len(overlap) >= 20:
            cov = overlap.cov().iloc[0, 1]
            var = overlap["bench"].var(ddof=1)
            metrics.beta = float(cov / var) if var > 0 else None
            metrics.correlation = float(overlap["asset"].corr(overlap["bench"]))
            # Compounded excess return
            asset_cum = (1 + overlap["asset"]).prod() - 1
            bench_cum = (1 + overlap["bench"]).prod() - 1
            metrics.excess_return = float(asset_cum - bench_cum)
            
    frame = technical_frame(df["close"])
    diagnostics = score_diagnostics(frame)
    
    return AnalysisResult(metrics=metrics, diagnostics=diagnostics)
