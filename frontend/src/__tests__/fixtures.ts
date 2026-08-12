import type {
  Instrument,
  PriceBar,
  AnalysisResult,
  AssetProfile,
  BacktestResult,
  ResponseMeta,
  Envelope,
} from '../api/types'

export const meta: ResponseMeta = {
  sources: ['AkShare'],
  fetched_at: '2026-08-08T00:00:00Z',
  cache_hit: false,
  is_demo: false,
  warnings: []
}

export const bars: PriceBar[] = [
  { code: '512480.SH', trade_date: '2026-01-05', open: 1.2, high: 1.26, low: 1.19, close: 1.25, volume: 1000, amount: 1250, source: 'AkShare', fetched_at: '2026-08-08T00:00:00Z' },
  { code: '512480.SH', trade_date: '2026-01-06', open: 1.25, high: 1.28, low: 1.22, close: 1.27, volume: 1100, amount: 1397, source: 'AkShare', fetched_at: '2026-08-08T00:00:00Z' }
]

export const analysis: AnalysisResult = {
  metrics: {
    annualized_return: 0.1,
    annualized_volatility: 0.15,
    downside: 0.1,
    sharpe: 0.5,
    sortino: 0.8,
    beta: 1.1,
    correlation: 0.9,
    excess_return: 0.02
  },
  diagnostics: {
    trend: { score: 80, rules: [] },
    momentum: { score: 60, rules: [] },
    volatility: { score: 90, rules: [] },
    drawdown: { score: 70, rules: [] }
  }
}

export const instrument: Instrument = {
  code: '512480.SH',
  name: '半导体 ETF',
  asset_type: 'etf',
  exchange: 'SH'
}

export const etfProfile: AssetProfile = {
  code: '512480.SH',
  asset_type: 'etf',
  etf: {
    tracking_index: '中证全指半导体产品与设备指数',
    tracking_index_code: 'H30184.CSI',
    manager: '华夏基金',
    inception_date: '2020-01-01',
    size: 5000000000,
    shares: 4000000000,
    size_change_20d: 0.05,
    share_change_20d: 0.02,
    turnover_rate: 0.03,
    nav: 1.24,
    premium_rate: 0.008,
    tracking_deviation: 0.001,
    holdings: [{ name: '中芯国际', weight: 0.1, code: '688981.SH' }],
    availability: { status: 'available', reason: null }
  },
  equity: null
}

export const equityProfile: AssetProfile = {
  code: '600519.SH',
  asset_type: 'equity',
  etf: null,
  equity: {
    industry: '食品饮料',
    valuation_trade_date: '2026-01-06',
    pe: 30,
    pb: 10,
    total_market_cap: 2000000000000,
    float_market_cap: 2000000000000,
    financial_periods: [
      { report_date: '2026-03-31', revenue: 30000000000, revenue_yoy: 0.15, net_profit: 15000000000, net_profit_yoy: 0.2, roe: 0.08, gross_margin: 0.9, net_margin: 0.5, debt_ratio: 0.2 }
    ],
    availability: { status: 'available', reason: null }
  }
}

export const backtestResult: BacktestResult = {
  request: { code: '512480.SH', start: '2025-08-08', end: '2026-08-08', fast_window: 20, slow_window: 60, fee_rate: 0.0003, slippage_rate: 0.0002, initial_cash: 100000 },
  metrics: { final_equity: 120000, annualized_return: 0.2, annualized_volatility: 0.15, sharpe: 1.2, max_drawdown: -0.1, trades_count: 2, win_rate: 1 },
  trades: [
    { signal_date: '2026-01-05', execution_date: '2026-01-06', direction: 'long', execution_price: 1.25, volume: 80000, fee: 30, slippage: 20 },
    { signal_date: '2026-02-05', execution_date: '2026-02-06', direction: 'close', execution_price: 1.45, volume: 80000, fee: 35, slippage: 23 }
  ],
  equity_curve: [
    { date: '2026-01-05', strategy: 100000, benchmark: 100000 },
    { date: '2026-02-06', strategy: 120000, benchmark: 110000 }
  ]
}

export const researchBundle = {
  instrument: { data: instrument, meta },
  market: { data: bars, meta },
  analysis: { data: analysis, meta },
  profile: { data: etfProfile, meta }
}
