import type { AssetProfile, ResponseMeta } from '../api/types'

const money = (value: number | null) => value === null ? '暂无数据' : `${(value / 1e8).toFixed(2)} 亿`
const ratio = (value: number | null) => value === null ? '暂无数据' : value.toFixed(2)

export default function AssetProfileView({ profile, meta }: { profile: AssetProfile; meta?: ResponseMeta }) {
  const sourceNote = meta ? `${meta.sources.join('、')} · 更新于 ${new Date(meta.fetched_at).toLocaleDateString('zh-CN')}` : null

  if (profile.asset_type === 'etf' && profile.etf) {
    const etf = profile.etf
    return (
      <section className="asset-profile" aria-label="ETF 基础资料">
        <div className="profile-meta"><span>{sourceNote}</span><span>资料字段为空时不使用估算值替代</span></div>
        {etf.availability.status === 'unavailable' ? <p className="profile-warning">{etf.availability.reason}</p> : null}
        <dl className="profile-facts">
          <div><dt>跟踪指数</dt><dd>{etf.tracking_index || '暂无数据'}</dd></div>
          <div><dt>基金管理人</dt><dd>{etf.manager || '暂无数据'}</dd></div>
          <div><dt>基金规模</dt><dd>{money(etf.size)}</dd></div>
          <div><dt>成立日期</dt><dd>{etf.inception_date || '暂无数据'}</dd></div>
        </dl>
        <div className="profile-holdings">
          <h3>前十大持仓</h3>
          {etf.holdings.length ? (
            <div>{etf.holdings.slice(0, 10).map((holding) => (
              <span key={`${holding.code}-${holding.name}`}><strong>{holding.name}</strong>{(holding.weight * 100).toFixed(2)}%</span>
            ))}</div>
          ) : <p>当前数据源没有返回持仓明细。</p>}
        </div>
      </section>
    )
  }

  if (profile.asset_type === 'equity' && profile.equity) {
    const equity = profile.equity
    return (
      <section className="asset-profile" aria-label="股票基础资料">
        <div className="profile-meta"><span>{sourceNote}</span><span>估值随市场变化，请结合数据日期查看</span></div>
        {equity.availability.status === 'unavailable' ? <p className="profile-warning">{equity.availability.reason}</p> : null}
        <dl className="profile-facts">
          <div><dt>所属行业</dt><dd>{equity.industry || '暂无数据'}</dd></div>
          <div><dt>市盈率（动态）</dt><dd>{ratio(equity.pe)}</dd></div>
          <div><dt>市净率</dt><dd>{ratio(equity.pb)}</dd></div>
          <div><dt>估值日期</dt><dd>{equity.valuation_trade_date || '暂无数据'}</dd></div>
          <div><dt>总市值</dt><dd>{money(equity.total_market_cap)}</dd></div>
          <div><dt>流通市值</dt><dd>{money(equity.float_market_cap)}</dd></div>
        </dl>
        <div className="profile-holdings">
          <h3>营业收入</h3>
          {equity.financial_periods.length ? (
            <div>{equity.financial_periods.slice(0, 4).map((period) => (
              <span key={period.report_date}><strong>报告期 {period.report_date}</strong>营收 {money(period.revenue)}</span>
            ))}</div>
          ) : <p>当前数据源没有返回标准化财务报告，未使用示例数字填充。</p>}
        </div>
      </section>
    )
  }

  return <div className="asset-profile"><p className="profile-warning">暂无资产资料</p></div>
}
