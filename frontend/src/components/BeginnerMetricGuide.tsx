import { CaretDown, ChartLineDown, ChartLineUp, Gauge, ShieldCheck, WaveSine } from '@phosphor-icons/react'
import { useState } from 'react'

const steps = [
  {
    label: '先看结果',
    title: '区间收益',
    question: '这段时间最终赚了还是亏了？',
    detail: '它说明起点到终点的结果，但没有告诉你持有过程是否平稳。',
    icon: ChartLineUp,
  },
  {
    label: '再看最坏情况',
    title: '最大回撤',
    question: '途中最多可能承受多大亏损？',
    detail: '它帮助你判断，自己是否能承受价格从高点跌到低点的压力。',
    icon: ChartLineDown,
  },
  {
    label: '再看日常体验',
    title: '年化波动',
    question: '平时的价格起伏有多剧烈？',
    detail: '波动越高，持有过程通常越颠簸，对仓位和耐心的要求也越高。',
    icon: WaveSine,
  },
  {
    label: '最后看效率',
    title: '夏普比率',
    question: '承担的风险换来了多少收益？',
    detail: '它把收益和波动放在一起比较，适合辅助判断风险是否得到补偿。',
    icon: Gauge,
  },
]

export default function BeginnerMetricGuide() {
  const [expanded, setExpanded] = useState(false)

  return (
    <section className={`beginner-metric-guide ${expanded ? 'is-expanded' : 'is-collapsed'}`} aria-labelledby="beginner-metric-guide-title">
      <header className="beginner-guide-trigger">
        <div>
          <span className="lesson-eyebrow">初学者阅读指南</span>
          <h2 id="beginner-metric-guide-title">怎么看这四项指标？</h2>
          <p>按结果、最坏情况、日常体验和风险收益效率，逐步理解四项指标。</p>
        </div>
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls="beginner-metric-guide-content"
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? '收起指南' : '展开指南'}
          <CaretDown size={16} weight="bold" aria-hidden="true" />
        </button>
      </header>

      {expanded ? (
        <div id="beginner-metric-guide-content" className="beginner-guide-content">
          <p className="beginner-guide-intro">不要只找一个“最好”的数字。按结果、最坏情况、日常体验和风险收益效率依次阅读，会更接近真实的持有感受。</p>
          <ol className="metric-reading-steps">
            {steps.map((step, index) => {
              const Icon = step.icon
              return (
                <li key={step.title}>
                  <div className="reading-step-heading">
                    <span>{String(index + 1).padStart(2, '0')}</span>
                    <Icon size={22} weight="duotone" aria-hidden="true" />
                  </div>
                  <small>{step.label}</small>
                  <h3>{step.title}</h3>
                  <strong>{step.question}</strong>
                  <p>{step.detail}</p>
                </li>
              )
            })}
          </ol>

          <div className="risk-return-example">
            <div>
              <span>同样一年赚 20%</span>
              <strong>A：途中最多跌 8%</strong>
              <strong>B：途中一度跌 45%</strong>
            </div>
            <p><strong>为什么要结合回撤？</strong>两者最终收益相同，但 B 承受的亏损压力明显更大，也更容易让人在低点卖出。因此，区间收益为正时，还要结合最大回撤和波动，判断这份收益承担了多少风险。</p>
          </div>

          <div className="score-boundary-note">
            <ShieldCheck size={20} weight="duotone" aria-hidden="true" />
            <span><strong>本页只评历史风险收益。</strong>四项分数分别判断，不与技术状态分合并。</span>
          </div>
        </div>
      ) : null}
    </section>
  )
}
