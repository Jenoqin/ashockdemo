import type { MetricKey } from '../api/types'

export interface LearningScore {
  score: number | null
  label: string
  basis: string
}

export function performanceLearningScore(key: MetricKey, value: number | null): LearningScore {
  if (value === null || Number.isNaN(value)) {
    return { score: null, label: '数据不足', basis: '样本不足，暂不评分' }
  }

  if (key === 'return') {
    if (value < -0.2) return { score: 15, label: '区间偏弱', basis: '区间收益低于 -20%' }
    if (value < 0) return { score: 35, label: '区间为负', basis: '区间收益低于 0%' }
    if (value < 0.1) return { score: 60, label: '温和为正', basis: '区间收益为 0%–10%' }
    if (value < 0.2) return { score: 80, label: '表现较强', basis: '区间收益为 10%–20%' }
    return { score: 95, label: '表现很强', basis: '区间收益不低于 20%' }
  }

  if (key === 'volatility') {
    if (value < 0.15) return { score: 90, label: '波动较低', basis: '年化波动低于 15%' }
    if (value < 0.3) return { score: 60, label: '波动中等', basis: '年化波动为 15%–30%' }
    return { score: 30, label: '波动偏高', basis: '年化波动不低于 30%' }
  }

  if (key === 'drawdown') {
    const depth = Math.abs(value)
    if (depth < 0.1) return { score: 90, label: '回撤温和', basis: '最大回撤小于 10%' }
    if (depth < 0.2) return { score: 60, label: '回撤中等', basis: '最大回撤为 10%–20%' }
    return { score: 30, label: '回撤较深', basis: '最大回撤不低于 20%' }
  }

  if (value < 0) return { score: 25, label: '效率偏弱', basis: '夏普比率低于 0' }
  if (value < 1) return { score: 60, label: '效率一般', basis: '夏普比率为 0–1' }
  return { score: 90, label: '效率较好', basis: '夏普比率不低于 1' }
}
