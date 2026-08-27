import { describe, expect, it } from 'vitest'
import { performanceLearningScore } from '../utils/learningScores'

describe('performanceLearningScore', () => {
  it('scores each performance dimension independently', () => {
    expect(performanceLearningScore('return', 0.12).score).toBe(80)
    expect(performanceLearningScore('volatility', 0.12).score).toBe(90)
    expect(performanceLearningScore('drawdown', -0.25).score).toBe(30)
    expect(performanceLearningScore('sharpe', 1.2).score).toBe(90)
  })

  it('does not turn missing data into a zero score', () => {
    expect(performanceLearningScore('return', null)).toEqual({
      score: null,
      label: '数据不足',
      basis: '样本不足，暂不评分',
    })
  })
})
