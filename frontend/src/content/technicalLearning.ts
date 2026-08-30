import type { TechnicalMetricKey } from '../api/types'

export interface TechnicalLesson {
  key: string
  name: string
  purpose: string
  principle: string
  formula: string
  symbols: string[]
  example: string
  misconception: string
}

export interface TechnicalLearningContent {
  label: string
  title: string
  intro: string
  lessons: TechnicalLesson[]
}

export const TECHNICAL_LEARNING_CONTENT: Record<TechnicalMetricKey, TechnicalLearningContent> = {
  trend: {
    label: '趋势状态',
    title: '趋势是如何从价格噪声里被看见的？',
    intro: '趋势不是对未来的保证，而是对当前价格是否呈现持续方向的描述。先用均线过滤短期噪声，再用 MACD 比较不同时间尺度，能把“方向”和“方向是否仍在加强”分开理解。',
    lessons: [
      {
        key: 'moving-average',
        name: '均线系统（MA20 / MA60）',
        purpose: '均线把一段时间内的收盘价压缩成一个价格中枢。价格与 MA20、MA20 与 MA60 的相对位置，以及 MA20 自身的方向，共同描述趋势结构。',
        principle: '市场价格同时包含长期变化和短期扰动。简单移动平均相当于低通滤波器：观察窗口越长，短期噪声被平滑得越多，但对新变化的反应也越慢。',
        formula: 'SMAₙ(t) = [Pₜ + P(t−1) + … + P(t−n+1)] / n；五日方向 = MA20ₜ − MA20(t−5)',
        symbols: ['Pₜ：第 t 个交易日收盘价', 'n：平均窗口，本页使用 20 或 60 个交易日', 'MA20(t−5)：五个交易日前的 20 日均线'],
        example: '若最近 20 个收盘价合计 24.00，MA20 = 24.00 ÷ 20 = 1.20。若 MA60 为 1.15，较短周期的价格中枢高于长期中枢。',
        misconception: '价格站上均线只说明当前相对位置，不代表随后一定上涨；均线本身来自历史价格，天然存在滞后。',
      },
      {
        key: 'macd-trend',
        name: 'MACD 趋势结构',
        purpose: 'MACD 比较快、慢两条指数移动平均。DIF 表示两个时间尺度之间的距离，DEA 对 DIF 再做平滑，柱线显示 DIF 偏离 DEA 的程度。',
        principle: '如果短周期平均值持续快于长周期平均值，说明近期价格中枢相对长期中枢抬升。对这段差值再平滑，可以减少一次性波动造成的误判。',
        formula: 'EMAₙ(t) = αPₜ + (1−α)EMAₙ(t−1)，α = 2/(n+1)；DIF = EMA12 − EMA26；DEA = EMA9(DIF)；柱线 = DIF − DEA',
        symbols: ['EMA12 / EMA26：快、慢指数移动平均', 'DIF：快慢均线差，本系统接口字段名为 MACD', 'DEA：DIF 的 9 日指数平均，即信号线', '柱线：DIF 与 DEA 的差，本系统不额外乘 2'],
        example: '若 EMA12 = 1.25、EMA26 = 1.20，则 DIF = 0.05；若 DEA = 0.03，柱线 = 0.02，为正值。',
        misconception: 'MACD 为正或金叉不是买入保证。震荡行情中快慢均线会频繁交叉，必须结合价格和均线方向。',
      },
    ],
  },
  momentum: {
    label: '动量状态',
    title: '动量为什么能描述近期力量？',
    intro: '动量关注价格在近期是否持续向某个方向移动。RSI 衡量上涨与下跌力量的比例，20 日收益衡量实际位移，MACD 柱线补充观察这种力量是否在加速。',
    lessons: [
      {
        key: 'rsi',
        name: 'RSI 14',
        purpose: 'RSI 把近 14 日平均上涨幅度与平均下跌幅度进行比较，并压缩到 0–100，方便比较不同价格水平的资产。',
        principle: '动量来自连续交易日中上涨和下跌幅度的不平衡。单看涨了几天会忽略幅度，RSI 同时考虑方向和大小，再用比例完成归一化。',
        formula: 'RS = Wilder平均上涨14 / Wilder平均下跌14；RSI = 100 − 100/(1 + RS)；Wilder平滑 α = 1/14',
        symbols: ['上涨幅度：max(Pₜ − P(t−1), 0)', '下跌幅度：max(P(t−1) − Pₜ, 0)', 'Wilder 平滑：当前值占 1/14，上一期平滑值占 13/14'],
        example: '若平均上涨幅度为 0.03、平均下跌幅度为 0.02，RS = 1.5，RSI = 100 − 100 ÷ 2.5 = 60。',
        misconception: 'RSI 超过 70 不等于马上下跌，低于 30 也不等于马上反弹；强趋势可以在极端区域停留很久。',
      },
      {
        key: 'return-20d',
        name: '20 个交易日收益',
        purpose: '它直接回答当前价格相对 20 个交易日前移动了多少，是最直观的中短期动量读数。',
        principle: '动量最朴素的定义就是一段固定时间里的净位移。它不平滑路径，也不区分途中波动，只比较起点和终点。',
        formula: 'R20ₜ = Pₜ / P(t−20) − 1',
        symbols: ['Pₜ：当前收盘价', 'P(t−20)：20 个交易日前的收盘价', '计算需要当前日加上此前 20 日，共 21 个价格观测点'],
        example: '若 20 个交易日前收盘价为 1.00，当前为 1.08，R20 = 1.08 ÷ 1.00 − 1 = 8%。',
        misconception: '20 日收益为正只说明这一段的终点更高，不代表上涨过程平稳，也不能推导下一个 20 日仍为正。',
      },
      {
        key: 'macd-momentum',
        name: 'MACD 动量确认',
        purpose: '在动量状态中，重点不是 DIF 是否位于零轴上方，而是 DIF 是否高于 DEA、柱线是否为正，用来观察近期力量是否强于其平滑基准。',
        principle: 'DEA 是 DIF 的低速版本；DIF 偏离 DEA 的部分相当于快变量相对慢基准的残差，可以近似理解为趋势变化的速度。',
        formula: '动量差 = DIF − DEA = MACD 柱线',
        symbols: ['DIF：EMA12 与 EMA26 的差', 'DEA：DIF 的 9 日指数平均', '柱线为正：DIF 当前高于自己的平滑基准'],
        example: '若 DIF = 0.026、DEA = 0.018，动量差 = 0.008；这表示近期趋势差高于其平滑值。',
        misconception: '柱线缩短只表示动量差收窄，不等于价格已经转跌；价格方向和动量变化需要分开判断。',
      },
    ],
  },
  volatility: {
    label: '波动状态',
    title: '波动为什么只谈幅度、不谈方向？',
    intro: '波动描述价格变化有多剧烈，而不是会上涨还是下跌。收益标准差、真实波幅和布林带宽度分别从收盘变化、日内与跳空、价格分布三个角度观察同一件事。',
    lessons: [
      {
        key: 'rolling-volatility',
        name: '20 日滚动年化波动',
        purpose: '它计算最近 20 个日收益率的标准差，再换算为一年尺度，用于比较不同时间区间的日常起伏。',
        principle: '如果日收益经常远离自己的平均值，价格路径就更不稳定。标准差测量这种离散程度，乘以 √252 来利用方差随时间近似累加的关系。',
        formula: 'rₜ = Pₜ/P(t−1) − 1；Vol20ₜ = Std(rₜ…r(t−19), ddof=1) × √252',
        symbols: ['rₜ：简单日收益率', 'Std：20 个日收益率的样本标准差', '252：A 股常用的年交易日经验值'],
        example: '若 20 日日收益标准差为 1.5%，年化波动约为 1.5% × √252 = 23.8%。',
        misconception: '高波动既可能来自大涨，也可能来自大跌；低波动也不意味着更安全或即将上涨。',
      },
      {
        key: 'atr',
        name: 'ATR 14 / 价格',
        purpose: 'ATR 衡量每天的真实波动范围，同时考虑日内高低差和隔夜跳空；除以价格后，才能在不同价位的资产之间比较。',
        principle: '仅用最高价减最低价会漏掉跳空。真实波幅取三个候选范围中的最大值，再用 Wilder 方法平滑，避免单日极端值完全主导判断。',
        formula: 'TRₜ = max(Hₜ−Lₜ, |Hₜ−C(t−1)|, |Lₜ−C(t−1)|)；ATR14 = Wilder平均(TR, 14)；ATR占比 = ATR14/Pₜ',
        symbols: ['Hₜ / Lₜ：当日最高价与最低价', 'C(t−1)：前一交易日收盘价', 'ATR14：真实波幅的 14 日 Wilder 平滑值'],
        example: '若三个候选范围为 0.04、0.06、0.03，则 TR = 0.06；若平滑 ATR 为 0.05、价格为 2.00，ATR 占比为 2.5%。',
        misconception: 'ATR 上升不区分涨跌方向，也不是买卖信号；它只说明价格活动范围正在扩大。',
      },
      {
        key: 'bollinger',
        name: '布林带与带宽',
        purpose: '布林带以 20 日均线为中心，用两倍标准差描述价格围绕均值的分布范围；带宽用相对比例表示这个范围有多宽。',
        principle: '价格越分散，标准差越大，上下轨距离越远。除以中轨可以消除价格绝对水平的影响，让不同阶段的宽度可比较。',
        formula: '中轨 = SMA20；上轨 = SMA20 + 2σ20；下轨 = SMA20 − 2σ20；带宽 = (上轨 − 下轨) / 中轨',
        symbols: ['σ20：最近 20 个收盘价的总体标准差，ddof=0', '2σ：本系统采用的经验带宽倍数', '带宽：上下轨距离相对中轨的比例'],
        example: '若中轨为 1.20、σ20 为 0.05，上轨为 1.30、下轨为 1.10，带宽 = 0.20 ÷ 1.20 = 16.7%。',
        misconception: '触及上轨不等于必须卖出，触及下轨也不等于必须买入；强趋势会沿着轨道持续运行。',
      },
    ],
  },
}
