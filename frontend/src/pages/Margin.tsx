import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import { useAppState } from '../appState'
import { DataLabel } from '../components/DataLabel'
import { SelectionBar } from '../components/SelectionBar'
import { ErrorBox, Loading } from '../components/Status'
import { formatRs, parseTypedNumber } from '../lib/format'
import { useAsync } from '../lib/useAsync'

/** Splits a price into cost of production, the farmer's own arhti commission, and what they keep (UC-08). */
export function Margin() {
  const { t } = useTranslation()
  const { selection, series, farmer } = useAppState()
  const latest = series(selection.crop, selection.mandi)?.latest_price
  const fromLatest = latest ? String(Math.round(latest)) : ''
  const [priceDraft, setPriceDraft] = useState({ forLatest: latest, text: fromLatest })
  const priceTyped = priceDraft.forLatest === latest ? priceDraft.text : fromLatest
  const setPriceTyped = (text: string) => setPriceDraft({ forLatest: latest, text })
  const [arhtiTyped, setArhtiTyped] = useState(farmer?.arhti_commission_pct != null ? String(farmer.arhti_commission_pct) : '')

  const price = parseTypedNumber(priceTyped)
  const arhti = arhtiTyped === '' ? null : parseTypedNumber(arhtiTyped)
  const ready = price !== null && price > 0
  const [state, reload] = useAsync(
    (signal) => (ready ? api.margin({ crop: selection.crop, price, arhti_pct: arhti }, signal) : Promise.reject(new Error('no price'))),
    `${selection.crop}|${price}|${arhti}`,
  )

  const input = 'figures w-36 rounded-xl border-2 border-line bg-paper px-3 py-2 text-lg focus:border-ink focus:outline-none'
  return (
    <div className="space-y-5">
      <SelectionBar />
      <section className="space-y-3 rounded-2xl bg-paper p-4 shadow-sm">
        <h2 className="text-xl font-bold">{t('margin.title')}</h2>
        <label className="block text-sm text-slate">
          {t('margin.price')}
          <input inputMode="decimal" value={priceTyped} onChange={(e) => setPriceTyped(e.target.value)} className={`${input} mt-1 block`} />
        </label>
        <label className="block text-sm text-slate">
          {t('margin.arhti')}
          <input inputMode="decimal" value={arhtiTyped} onChange={(e) => setArhtiTyped(e.target.value)} placeholder="0" className={`${input} mt-1 block`} />
        </label>
        {ready && state.status === 'loading' && <Loading />}
        {ready && state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
        {ready && state.status === 'ok' && (
          <>
            <Bar price={state.data.price} cost={state.data.production_cost} arhti={state.data.arhti_amount} />
            <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1">
              <dt>{t('margin.cost')}</dt>
              <dd className="figures">{formatRs(state.data.production_cost)}</dd>
              <dt>{t('margin.arhtiAmount')}</dt>
              <dd className="figures">{formatRs(state.data.arhti_amount)}</dd>
              <dt className="font-bold">{t('margin.profit')}</dt>
              <dd className={`figures font-bold ${state.data.profit >= 0 ? 'text-field' : 'text-madder'}`}>{formatRs(state.data.profit)}</dd>
            </dl>
            {state.data.support_price != null && state.data.support_status && (
              <p className="text-sm">
                {t('margin.support', {
                  price: formatRs(state.data.support_price),
                  year: state.data.support_crop_year,
                  status: t(`margin.supportStatus.${state.data.support_status}`),
                })}
              </p>
            )}
            <p className="text-xs text-slate">{t('margin.costNote', { confidence: state.data.cost_confidence })}</p>
            <DataLabel isSynthetic={state.data.is_synthetic} />
          </>
        )}
      </section>
    </div>
  )
}

/** One bar: cost, arhti, and what the farmer keeps (or the loss, in madder, when the price is below cost). */
function Bar({ price, cost, arhti }: { price: number; cost: number; arhti: number }) {
  const total = Math.max(price, cost + arhti)
  const pct = (x: number) => `${Math.max(0, (x / total) * 100)}%`
  const keep = price - cost - arhti
  return (
    <div className="flex h-6 w-full overflow-hidden rounded-full bg-line" aria-hidden>
      <div className="bg-ink/70" style={{ width: pct(cost) }} />
      <div className="bg-wheat" style={{ width: pct(arhti) }} />
      <div className={keep >= 0 ? 'bg-field' : 'bg-madder'} style={{ width: pct(Math.abs(keep)) }} />
    </div>
  )
}
