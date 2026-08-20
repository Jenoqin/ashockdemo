import { CaretDown, ChartLineUp, ChartScatter, Sparkle, Waveform } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import type { AnalysisResult, DateRangeKey, PriceBar } from '../api/types'
import MarketChart from './MarketChart'

type LessonKey = 'trend' | 'levels' | 'volume'

interface ResearchNoteProps {
  analysis: AnalysisResult
  bars: PriceBar[]
  range: DateRangeKey
  ranges: { label: string; key: DateRangeKey }[]
  onRangeChange: (range: DateRangeKey) => void
  aiNoticeVisible: boolean
  onAiClick: () => void
}

const formatPercent = (value: number | null | undefined) => (
  value === null || value === undefined ? '数据不足' : `${(value * 100).toFixed(2)}%`
)

const formatScore = (value: number | null | undefined) => (
  value === null || value === undefined ? '数据不足' : `${Math.round(value)}/100`
)

export default function ResearchNote({ analysis, bars, range, ranges, onRangeChange, aiNoticeVisible, onAiClick }: ResearchNoteProps) {
  const [lesson, setLesson] = useState<LessonKey>('trend')
  const { metrics, diagnostics } = analysis
  const annualReturn = metrics.annualized_return
  const volatility = metrics.annualized_volatility
  const trendScore = diagnostics.trend.score

  const insight = useMemo(() => {
    const direction = trendScore >= 70 ? '走势转强' : trendScore >= 50 ? '走势正在修复' : '方向仍偏弱'
    const risk = volatility === null || volatility === undefined
      ? '，风险数据还不完整'
      : volatility >= 0.3 ? '，但波动很大' : volatility >= 0.15 ? '，但仍要防大幅波动' : '，波动相对温和'
    return `${direction}${risk}`
  }, [trendScore, volatility])

  const startDate = bars[0]?.trade_date ?? '—'
  const endDate = bars[bars.length - 1]?.trade_date ?? '—'
  const lessons = [
    { key: 'trend' as const, number: 1, title: '先看整体斜率', note: '判断趋势方向与强弱', icon: ChartLineUp },
    { key: 'levels' as const, number: 2, title: '再看高低点', note: '识别支撑压力与区间', icon: ChartScatter },
    { key: 'volume' as const, number: 3, title: '最后看成交量', note: '验证动能变化与参与度', icon: Waveform },
  ]

  return (
    <article className="research-note">
      <div className="research-main">
        <section className="verdict-column" aria-labelledby="verdict-title">
          <p className="section-kicker">今天先记住一句话</p>
          <h1 id="verdict-title">{insight}</h1>
          <button type="button" className="ai-button" onClick={onAiClick} aria-expanded={aiNoticeVisible}>
            <Sparkle size={19} weight="fill" aria-hidden="true" />让 AI 帮我解释
          </button>
          {aiNoticeVisible ? <p className="ai-inline-notice">AI 量化解读入口已预留。后续会结合当前图表和指标，用新手能理解的语言逐段说明。</p> : null}

          <ol className="evidence-list">
            <li><span className="evidence-number tone-positive">1</span><div><h2>方向在回升</h2><p>价格自阶段低点反弹，整体斜率向上，趋势评分 <strong className="tone-positive">{formatScore(trendScore)}</strong>。</p></div></li>
            <li><span className="evidence-number tone-warning">2</span><div><h2>波动仍需留意</h2><p>年化波动率 <strong className="tone-warning">{formatPercent(volatility)}</strong>，持有过程可能仍会比较颠簸。</p></div></li>
            <li><span className="evidence-number tone-negative">3</span><div><h2>区间收益仍偏弱</h2><p>年化收益 <strong className="tone-negative">{formatPercent(annualReturn)}</strong>，说明当前回升尚未完全修复前期跌幅。</p></div></li>
          </ol>

          <p className="verdict-disclaimer">数据区间：{startDate} 至 {endDate}<br />过往表现不代表未来，本页仅用于学习。</p>
        </section>

        <section className="chart-story" aria-labelledby="chart-title">
          <div className="chart-story-header">
            <div><h2 id="chart-title">近{ranges.find((item) => item.key === range)?.label ?? '当前区间'} K 线</h2><span>{startDate} ～ {endDate}</span></div>
            <div className="range-picker" aria-label="选择图表区间">
              {ranges.map((item) => <button key={item.key} type="button" className={range === item.key ? 'is-active' : ''} aria-pressed={range === item.key} onClick={() => onRangeChange(item.key)}>{item.label}</button>)}
            </div>
          </div>

          <MarketChart bars={bars} analysis={analysis} lesson={lesson} />

          <div className="reading-order">
            <div className="reading-order-title"><ChartLineUp size={22} aria-hidden="true" /><strong>读图顺序</strong></div>
            <div className="lesson-tabs" role="tablist" aria-label="新手读图步骤">
              {lessons.map((item) => {
                const Icon = item.icon
                return <button key={item.key} type="button" role="tab" aria-selected={lesson === item.key} className={lesson === item.key ? 'is-active' : ''} onClick={() => setLesson(item.key)}><Icon size={23} weight="duotone" aria-hidden="true" /><span><strong>{item.number}&nbsp; {item.title}</strong><small>{item.note}</small></span></button>
              })}
            </div>
          </div>
        </section>
      </div>

      <details className="evidence-explanation" open>
        <summary><span>为什么这样判断？</span><span>收起证据 <CaretDown size={16} aria-hidden="true" /></span></summary>
        <div className="evidence-columns">
          <section><h2>证据一：整体斜率向上，趋势评分 <strong className="tone-positive">{formatScore(trendScore)}</strong></h2><p>先看图上最近一段的高点和低点是否依次抬高。它比单看某一天涨跌更能说明方向。</p><small>主要参考：趋势评分、均线排列与近期斜率</small></section>
          <section><h2>证据二：年化波动率 <strong className="tone-warning">{formatPercent(volatility)}</strong></h2><p>波动率衡量价格上下摆动的幅度。数值越高，持有过程中越容易遇到明显回撤。</p><small>公式提示：日收益率标准差 × √252</small></section>
          <section><h2>证据三：区间收益 <strong className="tone-negative">{formatPercent(annualReturn)}</strong></h2><p>区间收益仍为负，说明最近的回升还没有完全覆盖此前跌幅，不能只看右侧的上涨。</p><small>观察区间：{startDate} ～ {endDate}</small></section>
        </div>
      </details>
    </article>
  )
}
