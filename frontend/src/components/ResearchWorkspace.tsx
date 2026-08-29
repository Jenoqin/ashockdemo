import { BookOpenText, ChartLineDown, ChartLineUp, Lightbulb, Scales, ShieldCheck, Target, WaveSine } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import type { AnalysisResult, AssetProfile, DateRangeKey, Instrument, MetricKey, PriceBar, ResponseMeta } from '../api/types'
import { instrumentDisplayName } from '../utils/instrumentNames'
import { performanceLearningScore } from '../utils/learningScores'
import AssetProfileView from './AssetProfile'
import ChartDataTable, { type ChartDataColumn } from './ChartDataTable'
import BeginnerMetricGuide from './BeginnerMetricGuide'
import DateRangeControl from './DateRangeControl'
import MarketChart from './MarketChart'

interface ResearchWorkspaceProps {
  instrument: Instrument
  analysis: AnalysisResult
  bars: PriceBar[]
  profile: AssetProfile
  profileMeta: ResponseMeta
  range: DateRangeKey
  onRangeChange: (range: DateRangeKey) => void
}

interface MetricDefinition {
  key: MetricKey
  label: string
  value: number | null
  format: 'percent' | 'unsigned-percent' | 'ratio'
  icon: typeof ChartLineUp
  meaning: string
  impact: string
  experience: string
  evaluation: string
  score: ReturnType<typeof performanceLearningScore>
}

const formatMetric = (value: number | null, format: MetricDefinition['format']) => {
  if (value === null || Number.isNaN(value)) return '数据不足'
  if (format === 'ratio') return value.toFixed(2)
  const sign = format === 'percent' && value >= 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(1)}%`
}

const riskLabel = (volatility: number | null) => {
  if (volatility === null) return '风险数据不足'
  if (volatility >= 0.3) return '波动偏高'
  if (volatility >= 0.15) return '波动中等'
  return '波动较低'
}

export default function ResearchWorkspace({ instrument, analysis, bars, profile, profileMeta, range, onRangeChange }: ResearchWorkspaceProps) {
  const [activeMetric, setActiveMetric] = useState<MetricKey>('return')
  const { metrics, series } = analysis
  const displayName = instrumentDisplayName(instrument)

  const metricDefinitions = useMemo<MetricDefinition[]>(() => [
    {
      key: 'return', label: '区间收益', value: metrics.period_return, format: 'percent', icon: ChartLineUp,
      meaning: '区间收益表示从观察期开始持有到现在，资产价格累计上涨或下跌了多少。',
      impact: '收益决定结果，但不能单独说明过程是否平稳，也不能代表未来仍会延续。',
      experience: '需要同时和基准、波动及回撤一起看。主题类 ETF 的高收益常伴随更明显的价格起伏。',
      evaluation: metrics.period_return === null ? '当前样本不足，暂时无法评价。' : metrics.period_return > 0 ? `本期收益为正，累计${formatMetric(metrics.period_return, 'percent')}，下一步要确认这份收益承担了多少风险。` : `本期收益为负，累计${formatMetric(metrics.period_return, 'percent')}，应进一步查看回撤发生在何时。`,
      score: performanceLearningScore('return', metrics.period_return),
    },
    {
      key: 'volatility', label: '年化波动', value: metrics.annualized_volatility, format: 'unsigned-percent', icon: WaveSine,
      meaning: '波动率衡量每日收益上下变化的幅度，并换算成年化数值。',
      impact: '数值越高，短期涨跌越剧烈，持有体验越颠簸，对仓位和耐心要求也越高。',
      experience: '15% 以下通常较温和，15%–30% 属于中等波动，超过 30% 常见于高波动行业或主题资产。',
      evaluation: metrics.annualized_volatility === null ? '当前样本不足，暂时无法评价。' : `当前为 ${formatMetric(metrics.annualized_volatility, 'unsigned-percent')}，${riskLabel(metrics.annualized_volatility)}。经验区间只用于学习，不是买卖阈值。`,
      score: performanceLearningScore('volatility', metrics.annualized_volatility),
    },
    {
      key: 'drawdown', label: '最大回撤', value: metrics.max_drawdown, format: 'percent', icon: ChartLineDown,
      meaning: '最大回撤是观察期内，从一个历史高点跌到后续最低点的最大跌幅。',
      impact: '回撤越大，实际持有体验越差，需要更长时间和更强耐心等待价格修复。',
      experience: '宽基 ETF 回撤在 10% 内较温和，10%–20% 属于中等，超过 20% 表示持有压力明显。',
      evaluation: metrics.max_drawdown === null ? '当前样本不足，暂时无法评价。' : `本期最大回撤 ${formatMetric(metrics.max_drawdown, 'percent')}，${Math.abs(metrics.max_drawdown) > 0.2 ? '回撤较大' : Math.abs(metrics.max_drawdown) > 0.1 ? '处于中等区间' : '相对温和'}；当前回撤 ${formatMetric(metrics.current_drawdown, 'percent')}。`,
      score: performanceLearningScore('drawdown', metrics.max_drawdown),
    },
    {
      key: 'sharpe', label: '夏普比率', value: metrics.sharpe, format: 'ratio', icon: ShieldCheck,
      meaning: '夏普比率衡量每承担一份波动风险，获得了多少超过无风险收益的回报。',
      impact: '比率越高，说明风险换来的收益越有效；负值表示承担风险后仍未获得足够回报。',
      experience: '低于 0 表示风险回报较差，0–1 属于一般，超过 1 通常较好；短样本下容易失真。',
      evaluation: metrics.sharpe === null ? '当前样本不足，暂时无法评价。' : `当前夏普比率 ${formatMetric(metrics.sharpe, 'ratio')}，${metrics.sharpe >= 1 ? '风险收益效率较好' : metrics.sharpe >= 0 ? '风险收益效率一般' : '风险收益效率偏弱'}。`,
      score: performanceLearningScore('sharpe', metrics.sharpe),
    },
  ], [metrics])

  const active = metricDefinitions.find((item) => item.key === activeMetric) ?? metricDefinitions[0]
  const troughIndex = series.drawdown.reduce<number>((lowest, value, index) => {
    if (value === null) return lowest
    const current = series.drawdown[lowest]
    return current === null || value < current ? index : lowest
  }, 0)
  const returnTone = (metrics.period_return ?? 0) >= 0 ? 'positive' : 'negative'
  const summary = `${metrics.period_return === null ? '收益数据暂不完整' : metrics.period_return >= 0 ? '区间收益为正' : '区间收益为负'}，${riskLabel(metrics.annualized_volatility)}；先看最大回撤，再判断收益是否值得。`
  const chartColumns: ChartDataColumn[] = activeMetric === 'return'
    ? [
        { label: displayName, values: series.cumulative_return, format: 'percent' },
        ...(series.benchmark_return.some((value) => value !== null)
          ? [{ label: '跟踪基准', values: series.benchmark_return, format: 'percent' as const }]
          : []),
      ]
    : activeMetric === 'volatility'
      ? [{ label: '滚动20日年化波动', values: series.rolling_volatility, format: 'percent' }]
      : activeMetric === 'drawdown'
        ? [{ label: '回撤', values: series.drawdown, format: 'percent' }]
        : [{ label: '滚动60日夏普比率', values: series.rolling_sharpe, digits: 2 }]

  return (
    <article className="research-workspace">
      <section className="instrument-summary" aria-labelledby="instrument-title">
        <div>
          <h1 id="instrument-title">{displayName} <span>{instrument.code}</span></h1>
          <p><strong>一句话结论：</strong>{summary}</p>
        </div>
        <DateRangeControl range={range} onChange={onRangeChange} />
      </section>

      <dl className="quick-facts">
        <div><dt>区间表现</dt><dd className={`tone-${returnTone}`}>{formatMetric(metrics.period_return, 'percent')}</dd></div>
        <div><dt>持有波动</dt><dd>{riskLabel(metrics.annualized_volatility)}</dd></div>
        <div><dt>最大回撤发生日</dt><dd>{series.dates[troughIndex] ?? '数据不足'}</dd></div>
      </dl>

      <details className="profile-disclosure">
        <summary>
          <span>基础资料</span>
          <small>{instrument.asset_type === 'etf' ? '跟踪指数、基金规模与持仓' : '行业、估值与市值'}</small>
        </summary>
        <AssetProfileView profile={profile} meta={profileMeta} />
      </details>

      <div className="learning-layout">
        <nav className="metric-rail" aria-label="核心量化指标">
          {metricDefinitions.map((item) => {
            const Icon = item.icon
            const selected = item.key === activeMetric
            return (
              <button key={item.key} type="button" className={selected ? 'is-active' : ''} aria-pressed={selected} onClick={() => setActiveMetric(item.key)}>
                <span className="metric-icon"><Icon size={27} weight="duotone" aria-hidden="true" /></span>
                <span><small>{item.label}</small><strong>{formatMetric(item.value, item.format)}</strong><span className="metric-score-label">学习分 {item.score.score ?? '—'} / 100</span></span>
              </button>
            )
          })}
        </nav>

        <section className="chart-panel" aria-live="polite">
          <div className="chart-panel-heading">
            <div><strong>{active.label}</strong><span>点击左侧指标，图表与解释同步切换</span></div>
          </div>
          <MarketChart bars={bars} analysis={analysis} metric={activeMetric} instrumentName={displayName} />
          <ChartDataTable label={`查看${active.label}图表数据`} dates={series.dates} columns={chartColumns} />
        </section>

        <aside className="learning-panel" aria-label={`${active.label}解释`}>
          <section><h2><BookOpenText size={22} weight="duotone" />含义</h2><p>{active.meaning}</p></section>
          <section><h2><Scales size={22} weight="duotone" />影响</h2><p>{active.impact}</p></section>
          <section><h2><Lightbulb size={22} weight="duotone" />经验参考</h2><p>{active.experience}</p></section>
          <section><h2><Target size={22} weight="duotone" />当前评价</h2><p>{active.evaluation}</p></section>
          <section><h2><ShieldCheck size={22} weight="duotone" />评分口径</h2><p>{active.score.score === null ? active.score.basis : `${active.score.score} 分 · ${active.score.label}。${active.score.basis}；这是经验参考，不是买卖阈值。`}</p></section>
        </aside>
      </div>

      <BeginnerMetricGuide />
    </article>
  )
}
