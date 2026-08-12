import type { AssetProfile } from '../api/types'

export default function AssetProfileView({ profile }: { profile: AssetProfile }) {
  if (profile.asset_type === 'etf' && profile.etf) {
    const etf = profile.etf
    return (
      <div className="card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px' }}>
        <div>
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>跟踪指数</div>
          <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{etf.tracking_index || (etf.availability.status === 'unavailable' ? etf.availability.reason : '--')}</div>
        </div>
        <div>
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>规模 / 份额</div>
          <div style={{ fontSize: '16px', fontWeight: 'bold' }}>
            {etf.size ? `${(etf.size / 1e8).toFixed(2)}亿` : '--'} / {etf.shares ? `${(etf.shares / 1e8).toFixed(2)}亿` : '--'}
          </div>
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '16px' }}>前十大持仓</div>
          {etf.holdings.length > 0 ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {etf.holdings.map((h, i) => (
                <div key={i} style={{ padding: '8px', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)', fontSize: '14px' }}>
                  <span>{h.name}</span> <span style={{ color: 'var(--muted)', marginLeft: '8px' }}>{(h.weight * 100).toFixed(2)}%</span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: '14px' }}>{etf.availability.status === 'unavailable' ? etf.availability.reason : '无数据'}</div>
          )}
        </div>
      </div>
    )
  }

  if (profile.asset_type === 'equity' && profile.equity) {
    const equity = profile.equity
    return (
      <div className="card" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px' }}>
        <div>
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>所属行业</div>
          <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{equity.industry || (equity.availability.status === 'unavailable' ? equity.availability.reason : '--')}</div>
        </div>
        <div>
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '8px' }}>总市值 / 流通市值</div>
          <div style={{ fontSize: '16px', fontWeight: 'bold' }}>
            {equity.total_market_cap ? `${(equity.total_market_cap / 1e8).toFixed(2)}亿` : '--'} / {equity.float_market_cap ? `${(equity.float_market_cap / 1e8).toFixed(2)}亿` : '--'}
          </div>
        </div>
        <div style={{ gridColumn: '1 / -1' }}>
          <div style={{ color: 'var(--muted)', fontSize: '14px', marginBottom: '16px' }}>营业收入</div>
          {equity.financial_periods.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px' }}>
              {equity.financial_periods.slice(0, 4).map((p, i) => (
                <div key={i} style={{ padding: '12px', border: '1px solid var(--line)', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ color: 'var(--muted)', fontSize: '12px', marginBottom: '4px' }}>报告期 {p.report_date}</div>
                  <div style={{ fontSize: '16px', fontWeight: 'bold' }}>{p.revenue ? `${(p.revenue / 1e8).toFixed(2)}亿` : '--'}</div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--muted)', fontSize: '14px' }}>{equity.availability.status === 'unavailable' ? equity.availability.reason : '无数据'}</div>
          )}
        </div>
      </div>
    )
  }

  return <div className="card">无资产资料</div>
}
