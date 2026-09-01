import math
import numpy as np
import pandas as pd
from typing import List
from quantlab.models import BacktestRequest, BacktestResult, BacktestMetrics, TradeRecord, PriceBar
from quantlab.services.analytics import max_drawdown

def run_ma_cross(request: BacktestRequest, bars: List[PriceBar]) -> BacktestResult:
    request = BacktestRequest.model_validate(request.model_dump())
        
    if not bars:
        return BacktestResult(
            request=request,
            metrics=BacktestMetrics(final_equity=request.initial_cash, trades_count=0),
            trades=[],
            equity_curve=[]
        )
        
    df = pd.DataFrame([b.model_dump() for b in bars])
    df["fast"] = df["close"].rolling(request.fast_window).mean()
    df["slow"] = df["close"].rolling(request.slow_window).mean()
    
    # 信号生成：在收盘后形成
    df["prev_fast"] = df["fast"].shift(1)
    df["prev_slow"] = df["slow"].shift(1)
    
    df["signal"] = 0 # 0: 无, 1: 买, -1: 卖
    buy_cond = (df["prev_fast"] <= df["prev_slow"]) & (df["fast"] > df["slow"])
    sell_cond = (df["prev_fast"] >= df["prev_slow"]) & (df["fast"] < df["slow"])
    
    df.loc[buy_cond, "signal"] = 1
    df.loc[sell_cond, "signal"] = -1
    
    cash = request.initial_cash
    position = 0
    trades = []
    equity_curve = []
    
    pending_signal = 0
    signal_date = None
    
    # 指标热身区间：取最后一次移动平均线产生值的索引
    warmup_idx = df["slow"].first_valid_index()
    if warmup_idx is None:
        warmup_idx = len(df)
        
    benchmark_initial = None
        
    for i, row in df.iterrows():
        # 如果是热身期
        if i < warmup_idx:
            # 即使不计入策略绩效，也可以作为基准参考点
            continue
            
        # 设置基准起点
        if benchmark_initial is None:
            benchmark_initial = row["open"]
            benchmark_shares = request.initial_cash / benchmark_initial if benchmark_initial > 0 else 0
            
        current_date = row["trade_date"]
        
        # 盘前执行未决信号
        if pending_signal != 0 and pd.notna(row["open"]):
            price = float(row["open"])
            if pending_signal == 1 and position == 0:
                slippage_cost = price * request.slippage_rate
                exec_price = price + slippage_cost
                max_shares = math.floor(cash / (exec_price * (1 + request.fee_rate)))
                if max_shares > 0:
                    cost = max_shares * exec_price
                    fee = cost * request.fee_rate
                    total_cost = cost + fee
                    cash -= total_cost
                    position = max_shares
                    trades.append(TradeRecord(
                        signal_date=signal_date,
                        execution_date=current_date,
                        direction="long",
                        execution_price=exec_price,
                        volume=max_shares,
                        fee=fee,
                        slippage=max_shares * slippage_cost
                    ))
            elif pending_signal == -1 and position > 0:
                slippage_cost = price * request.slippage_rate
                exec_price = price - slippage_cost
                revenue = position * exec_price
                fee = revenue * request.fee_rate
                net_revenue = revenue - fee
                cash += net_revenue
                trades.append(TradeRecord(
                    signal_date=signal_date,
                    execution_date=current_date,
                    direction="close",
                    execution_price=exec_price,
                    volume=position,
                    fee=fee,
                    slippage=position * slippage_cost
                ))
                position = 0
                
            pending_signal = 0
            
        # 记录当前权益
        curr_price = float(row["close"])
        strat_equity = cash + position * curr_price
        bench_equity = benchmark_shares * curr_price if benchmark_initial else request.initial_cash
        
        equity_curve.append({
            "date": current_date.isoformat(),
            "strategy": strat_equity,
            "benchmark": bench_equity
        })
        
        # 盘后产生新信号
        if row["signal"] == 1:
            pending_signal = 1
            signal_date = current_date
        elif row["signal"] == -1:
            pending_signal = -1
            signal_date = current_date

    # 计算绩效指标
    if not equity_curve:
        metrics = BacktestMetrics(final_equity=cash, trades_count=0)
    else:
        eq_df = pd.DataFrame(equity_curve)
        returns = eq_df["strategy"].pct_change().dropna()
        
        if len(returns) > 0:
            ann_ret = (eq_df["strategy"].iloc[-1] / request.initial_cash) ** (252 / len(eq_df)) - 1
            ann_vol = returns.std(ddof=1) * np.sqrt(252)
            sharpe = ann_ret / ann_vol if ann_vol > 0 else None
            mdd, _ = max_drawdown(eq_df["strategy"])
        else:
            ann_ret = ann_vol = sharpe = mdd = None
            
        winning_trades = 0
        completed_trades = 0
        entry_price = 0
        for t in trades:
            if t.direction == "long":
                entry_price = t.execution_price
            elif t.direction == "close":
                completed_trades += 1
                # 简单计算胜率：退出价格是否大于买入价格，不含费用的近似计算
                if t.execution_price > entry_price:
                    winning_trades += 1
                    
        win_rate = winning_trades / completed_trades if completed_trades > 0 else None
        
        metrics = BacktestMetrics(
            final_equity=strat_equity,
            annualized_return=float(ann_ret) if ann_ret is not None else None,
            annualized_volatility=float(ann_vol) if ann_vol is not None else None,
            sharpe=float(sharpe) if sharpe is not None else None,
            max_drawdown=float(mdd) if mdd is not None else None,
            trades_count=len(trades),
            win_rate=float(win_rate) if win_rate is not None else None
        )
        
    return BacktestResult(
        request=request,
        metrics=metrics,
        trades=trades,
        equity_curve=equity_curve
    )

class BacktestService:
    pass
