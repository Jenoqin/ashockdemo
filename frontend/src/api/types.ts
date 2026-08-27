export type AssetType = 'etf' | 'equity'

export interface Instrument {
  code: string
  name: string
  full_name: string | null
  asset_type: AssetType
  exchange: 'SH' | 'SZ' | 'BJ'
}

export interface PriceBar {
  code: string
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number | null
  source: string
  fetched_at: string
}

export interface ScoreRule {
  label: string
  points: number
  triggered: boolean
  explanation: string
}

export interface DiagnosticCategory {
  score: number
  rules: ScoreRule[]
}

export interface Diagnostics {
  trend: DiagnosticCategory
  momentum: DiagnosticCategory
  volatility: DiagnosticCategory
  drawdown: DiagnosticCategory
  [key: string]: any
}

export interface PerformanceMetrics {
  period_return: number | null
  annualized_return: number | null
  annualized_volatility: number | null
  downside: number | null
  sharpe: number | null
  sortino: number | null
  max_drawdown: number | null
  max_drawdown_duration: number | null
  current_drawdown: number | null
  beta: number | null
  correlation: number | null
  excess_return: number | null
}

export interface AnalysisSeries {
  dates: string[]
  cumulative_return: Array<number | null>
  benchmark_return: Array<number | null>
  drawdown: Array<number | null>
  rolling_volatility: Array<number | null>
  rolling_sharpe: Array<number | null>
  ma20: Array<number | null>
  ma60: Array<number | null>
  macd: Array<number | null>
  macd_signal: Array<number | null>
  macd_hist: Array<number | null>
  rsi14: Array<number | null>
  boll_upper: Array<number | null>
  boll_mid: Array<number | null>
  boll_lower: Array<number | null>
  atr14_percent: Array<number | null>
}

export interface AnalysisResult {
  metrics: PerformanceMetrics
  diagnostics: Diagnostics
  series: AnalysisSeries
}

export type MetricKey = 'return' | 'volatility' | 'drawdown' | 'sharpe'
export type LearningPage = 'performance' | 'technical'
export type TechnicalMetricKey = 'trend' | 'momentum' | 'volatility'

export interface Availability {
  status: 'available' | 'unavailable'
  reason: string | null
}

export interface Holding {
  code: string | null
  name: string
  weight: number
}

export interface EtfProfile {
  tracking_index: string | null
  tracking_index_code: string | null
  manager: string | null
  inception_date: string | null
  size: number | null
  shares: number | null
  size_change_20d: number | null
  share_change_20d: number | null
  turnover_rate: number | null
  nav: number | null
  premium_rate: number | null
  tracking_deviation: number | null
  holdings: Holding[]
  availability: Availability
}

export interface FinancialPeriod {
  report_date: string
  revenue: number | null
  revenue_yoy: number | null
  net_profit: number | null
  net_profit_yoy: number | null
  roe: number | null
  gross_margin: number | null
  net_margin: number | null
  debt_ratio: number | null
}

export interface EquityProfile {
  industry: string | null
  valuation_trade_date: string | null
  pe: number | null
  pb: number | null
  total_market_cap: number | null
  float_market_cap: number | null
  turnover_rate: number | null
  financial_periods: FinancialPeriod[]
  availability: Availability
}

export interface AssetProfile {
  code: string
  asset_type: AssetType
  etf: EtfProfile | null
  equity: EquityProfile | null
}

export interface BacktestRequest {
  code: string
  start: string | null
  end: string | null
  fast_window: number
  slow_window: number
  fee_rate: number
  slippage_rate: number
  initial_cash: number
}

export interface TradeRecord {
  signal_date: string
  execution_date: string
  direction: 'long' | 'close'
  execution_price: number
  volume: number
  fee: number
  slippage: number
}

export interface BacktestMetrics {
  final_equity: number
  annualized_return: number | null
  annualized_volatility: number | null
  sharpe: number | null
  max_drawdown: number | null
  trades_count: number
  win_rate: number | null
}

export interface EquityCurvePoint {
  date: string
  strategy: number
  benchmark: number
}

export interface BacktestResult {
  request: BacktestRequest
  metrics: BacktestMetrics
  trades: TradeRecord[]
  equity_curve: EquityCurvePoint[]
}

export interface ResponseMeta {
  sources: string[]
  fetched_at: string
  cache_hit: boolean
  is_demo: boolean
  warnings: string[]
}

export interface Envelope<T> {
  data: T
  meta: ResponseMeta
}

export interface ApiError {
  code: string
  message: string
  action?: string
}

export type DateRangeKey = '1w' | '1m' | '3m' | '6m' | '1y' | '3y' | 'all'

export interface DateRange {
  start: string
  end: string
  key: DateRangeKey
}
