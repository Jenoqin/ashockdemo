import type { Instrument } from '../api/types'

interface InstrumentHeroProps {
  instrument: Instrument
}

export default function InstrumentHero({ instrument }: InstrumentHeroProps) {
  return (
    <div className="card" style={{ marginBottom: '24px' }}>
      <h2 style={{ margin: '0 0 8px 0', fontSize: '32px' }}>{instrument.name}</h2>
      <div style={{ color: 'var(--muted)' }}>
        {instrument.code} | {instrument.asset_type === 'etf' ? 'ETF' : '股票'} | {instrument.exchange}
      </div>
    </div>
  )
}
