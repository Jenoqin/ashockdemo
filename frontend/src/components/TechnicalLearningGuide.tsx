import { BookOpenText, CaretDown, Function, Lightbulb, ListChecks, WarningCircle } from '@phosphor-icons/react'
import { useState } from 'react'
import type { DiagnosticCategory, TechnicalMetricKey } from '../api/types'
import { TECHNICAL_LEARNING_CONTENT } from '../content/technicalLearning'

interface TechnicalLearningGuideProps {
  metric: TechnicalMetricKey
  score: DiagnosticCategory
  currentReadings: Record<string, string>
  scoreAvailable: boolean
}

export default function TechnicalLearningGuide({ metric, score, currentReadings, scoreAvailable }: TechnicalLearningGuideProps) {
  const [expanded, setExpanded] = useState(false)
  const content = TECHNICAL_LEARNING_CONTENT[metric]
  const passedRules = score.rules.filter((rule) => rule.triggered).length

  return (
    <section className={`technical-beginner-guide ${expanded ? 'is-expanded' : 'is-collapsed'}`} aria-labelledby="technical-beginner-guide-title">
      <header className="technical-guide-trigger">
        <div>
          <span className="lesson-eyebrow">新手学习指南</span>
          <h2 id="technical-beginner-guide-title">{content.title}</h2>
          <p>从含义、第一性原理和公式开始，逐项读懂{content.label}。</p>
        </div>
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls="technical-beginner-guide-content"
          onClick={() => setExpanded((current) => !current)}
        >
          {expanded ? '收起指南' : '展开指南'}
          <CaretDown size={16} weight="bold" aria-hidden="true" />
        </button>
      </header>

      {expanded ? (
        <div id="technical-beginner-guide-content" className="technical-guide-content" aria-live="polite">
          <p className="technical-guide-intro">{content.intro}</p>

          <div className="technical-lesson-list">
            {content.lessons.map((lesson, index) => (
              <article className="technical-lesson" key={lesson.key}>
                <header>
                  <span>{String(index + 1).padStart(2, '0')}</span>
                  <div>
                    <small>{content.label}指标</small>
                    <h3>{lesson.name}</h3>
                  </div>
                </header>

                <div className="technical-lesson-explanation">
                  <section>
                    <h4><BookOpenText size={19} weight="duotone" aria-hidden="true" />具体含义</h4>
                    <p>{lesson.purpose}</p>
                  </section>
                  <section>
                    <h4><Lightbulb size={19} weight="duotone" aria-hidden="true" />第一性原理</h4>
                    <p>{lesson.principle}</p>
                  </section>
                </div>

                <section className="technical-formula-block">
                  <h4><Function size={19} weight="duotone" aria-hidden="true" />公式</h4>
                  <code>{lesson.formula}</code>
                  <ul>{lesson.symbols.map((symbol) => <li key={symbol}>{symbol}</li>)}</ul>
                </section>

                <div className="technical-lesson-application">
                  <section>
                    <h4>当前读数</h4>
                    <p>{currentReadings[lesson.key] ?? '当前数据不足，暂时无法形成有效读数。'}</p>
                  </section>
                  <section>
                    <h4>教学示例</h4>
                    <p>{lesson.example}</p>
                  </section>
                </div>

                <p className="technical-misconception"><WarningCircle size={19} weight="duotone" aria-hidden="true" /><span><strong>不要误解：</strong>{lesson.misconception}</span></p>
              </article>
            ))}
          </div>

          <section className="technical-score-explainer">
            <header>
              <ListChecks size={23} weight="duotone" aria-hidden="true" />
              <div>
                <h3>本次规则满足度</h3>
                <p>{scoreAvailable ? `${passedRules}/${score.rules.length} 项满足，合计 ${score.score}/100。` : '历史样本不足，暂不计算规则满足度。'}分数是透明规则的加权结果，不是上涨概率。</p>
              </div>
            </header>
            {scoreAvailable ? (
              <ul>{score.rules.map((rule) => (
                <li key={rule.label} className={rule.triggered ? 'is-triggered' : ''}>
                  <span>{rule.triggered ? '已满足' : '未满足'}</span>
                  <div><strong>{rule.label} · {rule.points} 分</strong><small>{rule.explanation}</small></div>
                </li>
              ))}</ul>
            ) : null}
          </section>
        </div>
      ) : null}
    </section>
  )
}
