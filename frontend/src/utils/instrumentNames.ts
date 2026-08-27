import type { Instrument } from '../api/types'

export const instrumentDisplayName = (instrument: Instrument) =>
  instrument.full_name?.trim() || instrument.name

export const instrumentSearchMeta = (instrument: Instrument) => {
  const assetLabel = instrument.asset_type === 'etf' ? 'ETF' : '股票'
  return instrument.full_name && instrument.full_name !== instrument.name
    ? `${instrument.name} · ${assetLabel}`
    : assetLabel
}
