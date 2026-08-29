import { BookOpenText, Lightbulb, ListChecks, Pulse, Target, TrendUp, WarningCircle, WaveSine } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import type { AnalysisResult, DateRangeKey, DiagnosticCategory, Instrument, PriceBar, TechnicalMetricKey } from '../api/types'
import { instrumentDisplayName } from '../utils/instrumentNames'
import ChartDataTable, { type ChartDataColumn } from './ChartDataTable'
import DateRangeControl from './DateRangeControl'
import TechnicalChart from './TechnicalChart'

interface TechnicalWorkspaceProps {
  instrument: Instrument
  analysis: AnalysisResult
  bars: PriceBar[]
  range: DateRangeKey
  onRangeChange: (range: DateRangeKey) => void
}

interface TechnicalDefinition {
  key: TechnicalMetricKey
  label: string
  score: DiagnosticCategory
  icon: typeof TrendUp
  scoreMeaning: string
  meaning: string
  reading: string
  misconception: string
  values: Array<{ label: string; value: string }>
}

const lastNumber = (values: Array<number | null>) => {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    if (values[index] !== null && !Number.isNaN(values[index])) return values[index]
  }
  return null
}

const number = (value: number | null, digits = 2) => value === null ? '数据不足' : value.toFixed(digits)
const percent = (value: number | null) => value === null ? '数据不足' : `${(value * 100).toFixed(1)}%`
const scoreState = (score: number) => score >= 80 ? '条件较完整' : score >= 50 ? '部分条件满足' : '当前条件较少'

export default function TechnicalWorkspace({ instrument, analysis, bars, range, onRangeChange }: TechnicalWorkspaceProps) {
  const [activeMetric, setActiveMetric] = useState<TechnicalMetricKey>('trend')
  const { series, diagnostics } = analysis
  const displayName = instrumentDisplayName(instrument)

  const definitions = useMemo<TechnicalDefinition[]>(() => {
    const ma20 = lastNumber(series.ma20)
    const ma60 = lastNumber(series.ma60)
    const macd = lastNumber(series.macd)
    const signal = lastNumber(series.macd_signal)
    const rsi = lastNumber(series.rsi14)
    const atr = lastNumber(series.atr14_percent)
    const upper = lastNumber(series.boll_upper)
    const lower = lastNumber(series.boll_lower)
    const mid = lastNumber(series.boll_mid)
    const bollWidth = upper !== null && lower !== null && mid ? (upper - lower) / mid : null
    const return20 = bars.length >= 20 ? bars.at(-1)!.close / bars.at(-20)!.close - 1 : null

    return [
      {
        key: 'trend', label: '趋势状态', score: diagnostics.trend, icon: TrendUp,
        scoreMeaning: '分数越高，价格、均线与 MACD 的偏强趋势条件越完整。',
        meaning: 'MA 用平均价格过滤短期噪声；MACD 比较快慢趋势，观察趋势是否正在加强或减弱。',
        reading: '先看价格与 MA20、MA60 的相对位置，再看均线方向和 MACD 柱线是否相互印证。',
        misconception: '趋势分高只表示当前状态偏强，不代表估值便宜，也不保证随后继续上涨。',
        values: [
          { label: 'MA20', value: number(ma20, 3) },
          { label: 'MA60', value: number(ma60, 3) },
          { label: 'MACD', value: number(macd, 4) },
        ],
      },
      {
        key: 'momentum', label: '动量状态', score: diagnostics.momentum, icon: Pulse,
        scoreMeaning: '分数越高，近期上涨力量与 MACD 动量条件越充分，同时避免把明显过热直接当作更好。',
        meaning: 'RSI 比较近期上涨和下跌力量；MACD 信号线与近 20 日收益帮助确认动量是否持续。',
        reading: 'RSI 不是越高越好。45–70 常被视为偏强但未明显过热，超过 70 需要结合趋势判断。',
        misconception: '“超买”不等于马上下跌，“超卖”也不等于马上反弹；它们是状态描述，不是确定信号。',
        values: [
          { label: 'RSI 14', value: number(rsi, 1) },
          { label: '近 20 日', value: percent(return20) },
          { label: 'MACD 信号线', value: number(signal, 4) },
        ],
      },
      {
        key: 'volatility', label: '波动状态', score: diagnostics.volatility, icon: WaveSine,
        scoreMeaning: '分数越高，近期波动越温和或正在收敛；它不是上涨概率。',
        meaning: '布林带用均线和标准差描述价格分布区间；ATR 衡量每天真实波幅，不区分上涨或下跌。',
        reading: '布林带变宽与 ATR 上升通常表示行情更剧烈；收窄表示暂时平静，但不预测下一次突破方向。',
        misconception: 'ATR 上升既可能来自大涨，也可能来自大跌。接近布林上轨也不等于必须卖出。',
        values: [
          { label: 'ATR 14 / 价格', value: percent(atr) },
          { label: '布林带宽度', value: percent(bollWidth) },
          { label: '20 日年化波动', value: percent(lastNumber(series.rolling_volatility)) },
        ],
      },
    ]
  }, [bars, diagnostics, series])

  const active = definitions.find((item) => item.key === activeMetric) ?? definitions[0]
  const summary = `趋势 ${diagnostics.trend.score} 分、动量 ${diagnostics.momentum.score} 分、波动状态 ${diagnostics.volatility.score} 分；三项分别解释，不相加。`
  const closes = bars.map((bar) => bar.close)
  const chartColumns: ChartDataColumn[] = activeMetric === 'trend'
    ? [
        { label: displayName, values: closes, digits: 3 },
        { label: 'MA20', values: series.ma20, digits: 3 },
        { label: 'MA60', values: series.ma60, digits: 3 },
        { label: 'MACD', values: series.macd, digits: 4 },
        { label: '信号线', values: series.macd_signal, digits: 4 },
        { label: 'MACD 柱', values: series.macd_hist, digits: 4 },
      ]
    : activeMetric === 'momentum'
      ? [
          { label: 'RSI 14', values: series.rsi14, digits: 1 },
          { label: 'MACD', values: series.macd, digits: 4 },
          { label: '信号线', values: series.macd_signal, digits: 4 },
          { label: 'MACD 柱', values: series.macd_hist, digits: 4 },
        ]
      : [
          { label: displayName, values: closes, digits: 3 },
          { label: '布林上轨', values: series.boll_upper, digits: 3 },
          { label: '布林中轨', values: series.boll_mid, digits: 3 },
          { label: '布林下轨', values: series.boll_lower, digits: 3 },
          { label: 'ATR 14 / 价格', values: series.atr14_percent, format: 'percent' },
        ]

  return (
    <article className="research-workspace technical-workspace">
      <section className="instrument-summary" aria-labelledby="technical-title">
        <div>
          <h1 id="technical-title">{displayName} <span>{instrument.code}</span></h1>
          <p><strong>一句话结论：</strong>{summary}</p>
        </div>
        <DateRangeControl range={range} onChange={onRangeChange} />
      </section>

      <div className="learning-layout technical-learning-layout">
        <nav className="metric-rail" aria-label="技术状态指标">
          {definitions.map((item) => {
            const Icon = item.icon
            const selected = item.key === activeMetric
            return (
              <button key={item.key} type="button" className={selected ? 'is-active' : ''} aria-pressed={selected} onClick={() => setActiveMetric(item.key)}>
                <span className="metric-icon"><Icon size={27} weight="duotone" aria-hidden="true" /></span>
                <span><small>{item.label}</small><strong>{item.score.score}<em>/100</em></strong><span className="metric-score-label">{scoreState(item.score.score)}</span></span>
              </button>
            )
          })}
        </nav>

        <section className="chart-panel" aria-live="polite">
          <div className="chart-panel-heading">
            <div><strong>{active.label}</strong><span>切换左侧分项，图表、读法与评分规则同步更新</span></div>
          </div>
          <dl className="technical-values">
            {active.values.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}
          </dl>
          <TechnicalChart bars={bars} analysis={analysis} metric={activeMetric} instrumentName={displayName} />
          <ChartDataTable label={`查看${active.label}图表数据`} dates={series.dates} columns={chartColumns} />
        </section>

        <aside className="learning-panel technical-learning-panel" aria-label={`${active.label}解释`}>
          <section><h2><Target size={22} weight="duotone" />评分含义</h2><p>{active.scoreMeaning}</p></section>
          <section><h2><BookOpenText size={22} weight="duotone" />指标含义</h2><p>{active.meaning}</p></section>
          <section><h2><Lightbulb size={22} weight="duotone" />怎么读</h2><p>{active.reading}</p></section>
          <section><h2><WarningCircle size={22} weight="duotone" />不要误解</h2><p>{active.misconception}</p></section>
          <details className="score-rules">
            <summary><ListChecks size={22} weight="duotone" /><strong>本次得分规则</strong><span>{active.score.rules.filter((rule) => rule.triggered).length}/{active.score.rules.length} 项满足</span></summary>
            <ul>{active.score.rules.map((rule) => (
              <li key={rule.label} className={rule.triggered ? 'is-triggered' : ''}>
                <span>{rule.triggered ? '已满足' : '未满足'}</span>
                <div><strong>{rule.label} · {rule.points} 分</strong><small>{rule.explanation}</small></div>
              </li>
            ))}</ul>
          </details>
        </aside>
      </div>
    </article>
  )
}
