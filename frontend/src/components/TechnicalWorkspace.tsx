import { BookOpenText, Lightbulb, ListChecks, Pulse, ShieldCheck, Target, TrendUp, WarningCircle, WaveSine } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import type { AnalysisResult, DateRangeKey, DiagnosticCategory, Instrument, PriceBar, TechnicalMetricKey } from '../api/types'
import { instrumentDisplayName } from '../utils/instrumentNames'
import ChartDataTable, { type ChartDataColumn } from './ChartDataTable'
import DateRangeControl from './DateRangeControl'
import TechnicalChart from './TechnicalChart'
import TechnicalLearningGuide from './TechnicalLearningGuide'

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
  summary: string
  reading: string
  misconception: string
  values: Array<{ label: string; value: string }>
  currentReadings: Record<string, string>
  available: boolean
}

const lastNumber = (values: Array<number | null>) => {
  for (let index = values.length - 1; index >= 0; index -= 1) {
    if (values[index] !== null && !Number.isNaN(values[index])) return values[index]
  }
  return null
}

const number = (value: number | null, digits = 2) => value === null ? '数据不足' : value.toFixed(digits)
const percent = (value: number | null) => value === null ? '数据不足' : `${(value * 100).toFixed(1)}%`
const signedPercent = (value: number | null) => value === null ? '数据不足' : `${value >= 0 ? '+' : ''}${(value * 100).toFixed(1)}%`
const scoreState = (score: number) => score >= 80 ? '条件较完整' : score >= 50 ? '部分条件满足' : '当前条件较少'
const relation = (left: number, right: number) => left >= right ? '高于' : '低于'

export default function TechnicalWorkspace({ instrument, analysis, bars, range, onRangeChange }: TechnicalWorkspaceProps) {
  const [activeMetric, setActiveMetric] = useState<TechnicalMetricKey>('trend')
  const { series, diagnostics } = analysis
  const displayName = instrumentDisplayName(instrument)

  const definitions = useMemo<TechnicalDefinition[]>(() => {
    const close = bars.at(-1)?.close ?? null
    const ma20 = lastNumber(series.ma20)
    const ma60 = lastNumber(series.ma60)
    const macd = lastNumber(series.macd)
    const signal = lastNumber(series.macd_signal)
    const macdHist = lastNumber(series.macd_hist)
    const rsi = lastNumber(series.rsi14)
    const return20 = lastNumber(series.return_20d)
    const atr = lastNumber(series.atr14_percent)
    const rollingVolatility = lastNumber(series.rolling_volatility)
    const upper = lastNumber(series.boll_upper)
    const lower = lastNumber(series.boll_lower)
    const mid = lastNumber(series.boll_mid)
    const bollWidth = upper !== null && lower !== null && mid !== null && mid !== 0 ? (upper - lower) / mid : null

    const trendAvailable = close !== null && ma20 !== null && ma60 !== null && macd !== null && signal !== null && macdHist !== null
    const momentumAvailable = rsi !== null && return20 !== null && macd !== null && signal !== null && macdHist !== null
    const volatilityAvailable = rollingVolatility !== null && atr !== null && upper !== null && lower !== null && mid !== null && bollWidth !== null
    const movingAverageReading = close !== null && ma20 !== null && ma60 !== null
      ? `当前收盘价 ${number(close, 3)}，${relation(close, ma20)} MA20（${number(ma20, 3)}）；MA20 ${relation(ma20, ma60)} MA60（${number(ma60, 3)}）。`
      : '当前历史样本不足，暂时无法形成完整的 MA20 / MA60 趋势结构。'

    const rsiReading = rsi === null
      ? '当前历史样本不足，暂时无法计算 RSI 14。'
      : rsi > 70
        ? `当前 RSI 14 为 ${number(rsi, 1)}，位于经验上的偏热区域，需要结合趋势判断。`
        : rsi < 30
          ? `当前 RSI 14 为 ${number(rsi, 1)}，位于经验上的偏弱区域，不等于即将反弹。`
          : `当前 RSI 14 为 ${number(rsi, 1)}，处于 30–70 的常见中间区域。`

    const items: TechnicalDefinition[] = [
      {
        key: 'trend',
        label: '趋势状态',
        score: diagnostics.trend,
        icon: TrendUp,
        summary: '先看价格相对 MA20、MA60 的位置和均线方向，再用 MACD 判断快慢趋势差是否相互印证。',
        reading: '先确认价格是否站上 MA20，再看 MA20 与 MA60 的排列和方向，最后用 DIF、DEA 与柱线确认趋势是否同向。',
        misconception: '趋势分高只说明当前偏强条件较完整，不代表价格会持续上涨，也不是单独的买入信号。',
        available: trendAvailable,
        values: [
          { label: '当前收盘 / MA20', value: close === null || ma20 === null ? '数据不足' : `${number(close, 3)} / ${number(ma20, 3)}` },
          { label: 'MA20 / MA60', value: ma20 === null || ma60 === null ? '数据不足' : `${number(ma20, 3)} / ${number(ma60, 3)}` },
          { label: 'MACD 柱线', value: number(macdHist, 4) },
        ],
        currentReadings: {
          'moving-average': movingAverageReading,
          'macd-trend': macd !== null && signal !== null && macdHist !== null
            ? `当前 DIF 为 ${number(macd, 4)}，DEA 为 ${number(signal, 4)}，柱线为 ${number(macdHist, 4)}；DIF ${relation(macd, signal)}其平滑信号线。`
            : '当前历史样本不足，暂时无法形成完整的 MACD 读数。',
        },
      },
      {
        key: 'momentum',
        label: '动量状态',
        score: diagnostics.momentum,
        icon: Pulse,
        summary: '用 RSI 比较近期涨跌力量，用 20 日收益确认实际位移，再用 MACD 柱线观察这股力量是否仍在加速。',
        reading: '先用 RSI 判断力量落在哪个区间，再看 20 日收益的方向，最后观察 MACD 柱线是扩张还是收敛。',
        misconception: 'RSI 超过 70 不等于马上下跌，低于 30 也不等于马上反弹；极值可以在强趋势中维持很久。',
        available: momentumAvailable,
        values: [
          { label: 'RSI 14', value: number(rsi, 1) },
          { label: '20 个交易日收益', value: signedPercent(return20) },
          { label: 'MACD 柱线', value: number(macdHist, 4) },
        ],
        currentReadings: {
          rsi: rsiReading,
          'return-20d': return20 === null
            ? '当前历史样本不足，计算 20 个交易日收益至少需要 21 个收盘价。'
            : `当前 20 个交易日收益为 ${signedPercent(return20)}，只描述这一段起点到终点的净位移。`,
          'macd-momentum': macd !== null && signal !== null && macdHist !== null
            ? `当前 DIF 为 ${number(macd, 4)}、DEA 为 ${number(signal, 4)}，动量差为 ${number(macdHist, 4)}，目前${macdHist >= 0 ? '为正' : '为负'}。`
            : '当前历史样本不足，暂时无法形成完整的 MACD 动量读数。',
        },
      },
      {
        key: 'volatility',
        label: '波动状态',
        score: diagnostics.volatility,
        icon: WaveSine,
        summary: '分别从收盘收益离散度、日内与跳空幅度、价格围绕均值的分布宽度，理解近期行情有多剧烈。',
        reading: '先看年化波动判断收益序列的离散度，再用 ATR 衡量单日真实波幅，最后看布林带宽度是否扩张。',
        misconception: '波动高只代表价格变化更剧烈，不直接等于趋势向下；低波动也可能在突破前突然扩张。',
        available: volatilityAvailable,
        values: [
          { label: '20 日年化波动', value: percent(rollingVolatility) },
          { label: 'ATR 14 / 价格', value: percent(atr) },
          { label: '布林带宽度', value: percent(bollWidth) },
        ],
        currentReadings: {
          'rolling-volatility': rollingVolatility === null
            ? '当前历史样本不足，暂时无法计算 20 日滚动年化波动。'
            : `当前 20 日年化波动为 ${percent(rollingVolatility)}；数值越高，说明近期日收益的离散程度越大。`,
          atr: atr === null
            ? '当前历史样本不足，暂时无法计算 ATR 14。'
            : `当前 ATR 14 占价格 ${percent(atr)}，表示近期每日真实波幅相对当前价格的典型比例。`,
          bollinger: bollWidth === null || upper === null || mid === null || lower === null
            ? '当前历史样本不足，暂时无法形成完整的布林带读数。'
            : `当前上轨 ${number(upper, 3)}、中轨 ${number(mid, 3)}、下轨 ${number(lower, 3)}，带宽为 ${percent(bollWidth)}。`,
        },
      },
    ]
    return items
  }, [bars, diagnostics, series])

  const active = definitions.find((item) => item.key === activeMetric) ?? definitions[0]
  const passedRules = active.score.rules.filter((rule) => rule.triggered).length
  const summary = definitions.map((item) => `${item.label.replace('状态', '')} ${item.available ? `${item.score.score} 分` : '数据不足'}`).join('、')
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
          <span className="lesson-eyebrow">技术状态课</span>
          <h1 id="technical-title">{displayName} <span>{instrument.code}</span></h1>
          <p><strong>一句话结论：</strong>{summary}；三项分别解释，不相加。</p>
        </div>
        <DateRangeControl range={range} onChange={onRangeChange} />
      </section>

      <div className="learning-layout technical-learning-layout">
        <nav className="metric-rail" aria-label="技术状态指标">
          {definitions.map((item) => {
            const Icon = item.icon
            const selected = item.key === activeMetric
            return (
              <button
                key={item.key}
                type="button"
                aria-pressed={selected}
                className={selected ? 'is-active' : ''}
                onClick={() => setActiveMetric(item.key)}
              >
                <span className="metric-icon"><Icon size={27} weight="duotone" aria-hidden="true" /></span>
                <span>
                  <small>{item.label}</small>
                  <strong>{item.available ? item.score.score : '—'}<em>/100</em></strong>
                  <span className="metric-score-label">{item.available ? scoreState(item.score.score) : '样本不足'}</span>
                </span>
              </button>
            )
          })}
        </nav>

        <section className="chart-panel" aria-live="polite">
          <div className="chart-panel-heading">
            <div><strong>{active.label}</strong><span>点击左侧状态，图表与解释同步切换</span></div>
          </div>
          <dl className="technical-values">
            {active.values.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}
          </dl>
          <TechnicalChart bars={bars} analysis={analysis} metric={activeMetric} instrumentName={displayName} />
          <ChartDataTable label={`查看${active.label}图表数据`} dates={series.dates} columns={chartColumns} />
        </section>

        <aside className="learning-panel technical-learning-panel" aria-label={`${active.label}解释`}>
          <section><h2><BookOpenText size={22} weight="duotone" />含义</h2><p>{active.summary}</p></section>
          <section><h2><Lightbulb size={22} weight="duotone" />观察顺序</h2><p>{active.reading}</p></section>
          <section><h2><Target size={22} weight="duotone" />当前评价</h2><p>{active.available ? `${active.score.score} 分 · ${scoreState(active.score.score)}，当前满足 ${passedRules}/${active.score.rules.length} 项规则。` : '历史样本不足，暂不计算规则满足度。'}</p></section>
          <section><h2><WarningCircle size={22} weight="duotone" />常见误区</h2><p>{active.misconception}</p></section>
          <section>
            <h2><ShieldCheck size={22} weight="duotone" />评分口径</h2>
            <p>分数是透明规则的加权结果，只描述当前条件完整度，不是上涨概率。</p>
            <details className="score-rules">
              <summary><ListChecks size={19} weight="duotone" /><strong>查看评分规则</strong><span>{active.available ? `${passedRules}/${active.score.rules.length}` : '暂不可用'}</span></summary>
              <ul>
                {active.score.rules.map((rule) => (
                  <li key={rule.label} className={active.available && rule.triggered ? 'is-triggered' : ''}>
                    <span>{rule.points} 分</span>
                    <div><strong>{rule.label}</strong><small>{active.available ? rule.explanation : '等待足够历史数据'}</small></div>
                  </li>
                ))}
              </ul>
            </details>
          </section>
        </aside>
      </div>

      <TechnicalLearningGuide metric={activeMetric} score={active.score} currentReadings={active.currentReadings} scoreAvailable={active.available} />
    </article>
  )
}
