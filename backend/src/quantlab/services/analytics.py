import numpy as np
import pandas as pd
from typing import Tuple, Optional
from quantlab.models import AnalysisResult, AnalysisSeries, DiagnosticCategory, Diagnostics, PerformanceMetrics, PriceBar, ScoreRule

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

def technical_frame(
    close: pd.Series,
    high: Optional[pd.Series] = None,
    low: Optional[pd.Series] = None,
) -> pd.DataFrame:
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

    if high is not None and low is not None:
        previous_close = close.shift(1)
        true_range = pd.concat(
            [
                high - low,
                (high - previous_close).abs(),
                (low - previous_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr14 = true_range.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        df["atr14_percent"] = atr14 / close
    else:
        df["atr14_percent"] = np.nan
    
    return df

def score_diagnostics(frame: pd.DataFrame) -> Diagnostics:
    if len(frame) == 0:
        empty = DiagnosticCategory(score=0, rules=[])
        return Diagnostics(trend=empty, momentum=empty, volatility=empty, drawdown=empty)
        
    last = frame.iloc[-1]
    
    # Trend
    t_rules = []
    close_above_ma20 = pd.notna(last["close"]) and pd.notna(last["ma20"]) and last["close"] > last["ma20"]
    t_rules.append(ScoreRule(label="价格站上 MA20", points=30, triggered=bool(close_above_ma20), explanation="当前价格高于近 20 日平均价格"))
    
    ma20_above_ma60 = pd.notna(last["ma20"]) and pd.notna(last["ma60"]) and last["ma20"] > last["ma60"]
    t_rules.append(ScoreRule(label="MA20 高于 MA60", points=30, triggered=bool(ma20_above_ma60), explanation="中短期平均价格高于较长期平均价格"))
    
    if len(frame) >= 5:
        ma20_slope = frame["ma20"].iloc[-1] - frame["ma20"].iloc[-5]
        slope_pos = pd.notna(ma20_slope) and ma20_slope > 0
    else:
        slope_pos = False
    t_rules.append(ScoreRule(label="MA20 最近 5 日上行", points=20, triggered=bool(slope_pos), explanation="20 日均线较 5 个交易日前抬升"))
    
    macd_pos = pd.notna(last["macd_hist"]) and last["macd_hist"] > 0
    t_rules.append(ScoreRule(label="MACD 柱线为正", points=20, triggered=bool(macd_pos), explanation="快慢趋势差当前处于信号线上方"))
    
    t_score = sum(r.points for r in t_rules if r.triggered)
    
    # Momentum
    m_rules = []
    rsi_range = pd.notna(last["rsi14"]) and 45 <= last["rsi14"] <= 70
    m_rules.append(ScoreRule(label="RSI 位于 45–70", points=35, triggered=bool(rsi_range), explanation="近期上涨力量较强，但尚未进入经验上的过热区"))
    
    if len(frame) >= 20:
        ret20 = frame["close"].iloc[-1] / frame["close"].iloc[-20] - 1
        ret20_pos = pd.notna(ret20) and ret20 > 0
    else:
        ret20_pos = False
    m_rules.append(ScoreRule(label="近 20 日收益为正", points=35, triggered=bool(ret20_pos), explanation="当前价格高于约 20 个交易日前"))
    
    macd_above_signal = pd.notna(last["macd"]) and pd.notna(last["macd_signal"]) and last["macd"] > last["macd_signal"]
    m_rules.append(ScoreRule(label="MACD 高于信号线", points=30, triggered=bool(macd_above_signal), explanation="短期趋势动量强于平滑后的信号线"))
    
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
    vol_rules.append(ScoreRule(label="20 日波动低于近 60 日中位数", points=30, triggered=bool(vol_below_med), explanation="近期价格起伏低于自身近 60 日的典型水平"))
    
    if len(roll_vol20) >= 6:
        curr_vol20 = roll_vol20.iloc[-1]
        prev_vol20 = roll_vol20.iloc[-6]
        vol_lower = pd.notna(curr_vol20) and pd.notna(prev_vol20) and curr_vol20 < prev_vol20
    else:
        vol_lower = False
    vol_rules.append(ScoreRule(label="20 日波动较 5 日前下降", points=20, triggered=bool(vol_lower), explanation="近期波动正在收敛而不是继续放大"))

    atr = frame["atr14_percent"]
    if len(atr) >= 60:
        atr_median60 = atr.rolling(60, min_periods=20).median().iloc[-1]
        current_atr = atr.iloc[-1]
        atr_below_median = pd.notna(current_atr) and pd.notna(atr_median60) and current_atr < atr_median60
    else:
        atr_below_median = False
    vol_rules.append(ScoreRule(label="ATR 占比低于近 60 日中位数", points=25, triggered=bool(atr_below_median), explanation="当日真实波幅相对价格处于自身较温和区间"))

    boll_width = (frame["boll_upper"] - frame["boll_lower"]) / frame["boll_mid"]
    if len(boll_width) >= 60:
        width_median60 = boll_width.rolling(60, min_periods=20).median().iloc[-1]
        current_width = boll_width.iloc[-1]
        width_below_median = pd.notna(current_width) and pd.notna(width_median60) and current_width < width_median60
    else:
        width_below_median = False
    vol_rules.append(ScoreRule(label="布林带宽度低于近 60 日中位数", points=25, triggered=bool(width_below_median), explanation="价格围绕均线的分布区间相对收窄"))
    
    v_score = sum(r.points for r in vol_rules if r.triggered)
    
    # Drawdown
    d_rules = []
    running_max = frame["close"].cummax()
    drawdowns = (frame["close"] - running_max) / running_max
    
    curr_dd = drawdowns.iloc[-1] if len(drawdowns) > 0 else 0
    dd_above_10 = pd.notna(curr_dd) and curr_dd > -0.10
    d_rules.append(ScoreRule(label="当前回撤小于 10%", points=40, triggered=bool(dd_above_10), explanation="当前价格距离区间高点不足 10%"))
    
    max_dd, max_dur = max_drawdown(frame["close"])
    max_dd_above_20 = max_dd > -0.20
    d_rules.append(ScoreRule(label="最大回撤小于 20%", points=30, triggered=bool(max_dd_above_20), explanation="观察区间最深跌幅未超过 20%"))
    
    dur_below_60 = max_dur <= 60
    d_rules.append(ScoreRule(label="最长回撤不超过 60 日", points=30, triggered=bool(dur_below_60), explanation="最长水下阶段不超过约 60 个交易日"))
    
    d_score = sum(r.points for r in d_rules if r.triggered)
    
    return Diagnostics(
        trend=DiagnosticCategory(score=t_score, rules=t_rules),
        momentum=DiagnosticCategory(score=m_score, rules=m_rules),
        volatility=DiagnosticCategory(score=v_score, rules=vol_rules),
        drawdown=DiagnosticCategory(score=d_score, rules=d_rules)
    )

def analyze_market(
    bars: list[PriceBar],
    benchmark_bars: list[PriceBar] | None = None,
    risk_free_rate: float = 0.02,
    history_bars: list[PriceBar] | None = None,
) -> AnalysisResult:
    if not bars:
        return AnalysisResult(metrics=PerformanceMetrics(), diagnostics=score_diagnostics(pd.DataFrame()))
        
    df = pd.DataFrame([b.model_dump() for b in bars])
    returns = df["close"].pct_change()
    metrics = performance_metrics(returns, risk_free_rate=risk_free_rate)
    metrics.period_return = float(df["close"].iloc[-1] / df["close"].iloc[0] - 1)
    metrics.max_drawdown, metrics.max_drawdown_duration = max_drawdown(df["close"])
    running_max = df["close"].cummax()
    drawdown = (df["close"] - running_max) / running_max
    metrics.current_drawdown = float(drawdown.iloc[-1])

    cumulative_return = df["close"] / df["close"].iloc[0] - 1
    context_by_date = {
        bar.trade_date: bar for bar in (history_bars or bars)
    }
    context_by_date.update({bar.trade_date: bar for bar in bars})
    context_df = pd.DataFrame([
        bar.model_dump()
        for bar in sorted(context_by_date.values(), key=lambda bar: bar.trade_date)
    ])
    context_returns = context_df["close"].pct_change()
    context_rolling_volatility = context_returns.rolling(20).std(ddof=1) * np.sqrt(252)
    context_rolling_return = (1 + context_returns).rolling(60).apply(np.prod, raw=True) ** (252 / 60) - 1
    context_rolling_sharpe = (context_rolling_return - risk_free_rate) / (
        context_returns.rolling(60).std(ddof=1) * np.sqrt(252)
    )
    rolling_volatility_by_date = pd.Series(
        context_rolling_volatility.to_numpy(), index=context_df["trade_date"]
    )
    rolling_sharpe_by_date = pd.Series(
        context_rolling_sharpe.to_numpy(), index=context_df["trade_date"]
    )
    rolling_volatility = df["trade_date"].map(rolling_volatility_by_date)
    rolling_sharpe = df["trade_date"].map(rolling_sharpe_by_date)
    benchmark_return = pd.Series([np.nan] * len(df), index=df.index, dtype=float)
    
    if benchmark_bars:
        bench_df = pd.DataFrame([b.model_dump() for b in benchmark_bars])
        benchmark_by_date = bench_df.set_index("trade_date")["close"]
        aligned_benchmark = df["trade_date"].map(benchmark_by_date)
        first_valid = aligned_benchmark.first_valid_index()
        if first_valid is not None:
            benchmark_return = aligned_benchmark / aligned_benchmark.loc[first_valid] - 1
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

    frame = technical_frame(df["close"], df["high"], df["low"])
    diagnostics = score_diagnostics(frame)

    def optional_values(series: pd.Series) -> list[float | None]:
        return [None if pd.isna(value) else float(value) for value in series]

    return AnalysisResult(
        metrics=metrics,
        diagnostics=diagnostics,
        series=AnalysisSeries(
            dates=df["trade_date"].tolist(),
            cumulative_return=optional_values(cumulative_return),
            benchmark_return=optional_values(benchmark_return),
            drawdown=optional_values(drawdown),
            rolling_volatility=optional_values(rolling_volatility),
            rolling_sharpe=optional_values(rolling_sharpe),
            ma20=optional_values(frame["ma20"]),
            ma60=optional_values(frame["ma60"]),
            macd=optional_values(frame["macd"]),
            macd_signal=optional_values(frame["macd_signal"]),
            macd_hist=optional_values(frame["macd_hist"]),
            rsi14=optional_values(frame["rsi14"]),
            boll_upper=optional_values(frame["boll_upper"]),
            boll_mid=optional_values(frame["boll_mid"]),
            boll_lower=optional_values(frame["boll_lower"]),
            atr14_percent=optional_values(frame["atr14_percent"]),
        ),
    )
