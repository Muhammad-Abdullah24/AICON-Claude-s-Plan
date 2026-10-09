import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type CropPlanItem } from '../api/client'
import { useAppState } from '../appState'
import { ChipGroup } from '../components/ChipGroup'
import { DataLabel } from '../components/DataLabel'
import { ErrorBox, Loading } from '../components/Status'
import type { Lang } from '../i18n'
import { formatDate, formatMonth, formatRs, parseTypedNumber } from '../lib/format'
import { inSeason } from '../lib/months'
import { useAsync } from '../lib/useAsync'

const RISK_STYLE = { LOW: 'bg-field text-paper', MEDIUM: 'bg-wheat text-ink', HIGH: 'bg-madder text-paper' } as const

/** Crop options ranked by expected profit at harvest, each with its season and best selling month (UC-05, UC-06). */
export function Grow() {
  const { t } = useTranslation()
  const { meta, farmer, name, cropName } = useAppState()
  const [mandi, setMandi] = useState<string>(farmer?.district ?? 'bahawalpur')
  const [landTyped, setLandTyped] = useState(String(farmer?.land_area_acres ?? 10))
  const land = parseTypedNumber(landTyped)
  const acres = land !== null && land > 0 ? land : undefined
  const [state, reload] = useAsync(
    (signal) => api.cropPlan({ mandi, land_area_acres: acres }, signal),
    `${mandi}|${acres ?? ''}`,
  )

  return (
    <div className="space-y-5">
      <div className="space-y-4 rounded-2xl bg-paper p-4 shadow-sm">
        <ChipGroup
          label={t('select.mandi')}
          options={meta.mandis.map((m) => ({ value: m.id, label: name(m) }))}
          value={mandi}
          onChange={setMandi}
        />
        <div>
          <label htmlFor="land" className="mb-1 block text-sm text-slate">
            {t('grow.land')}
          </label>
          <div className="flex items-center gap-2">
            <input
              id="land"
              inputMode="decimal"
              value={landTyped}
              onChange={(e) => setLandTyped(e.target.value)}
              className="figures w-28 rounded-xl border-2 border-line bg-paper px-3 py-2 text-xl focus:border-ink focus:outline-none"
            />
            <span>{t('grow.acres')}</span>
          </div>
        </div>
      </div>

      <h2 className="text-xl font-bold">{t('grow.title')}</h2>
      {state.status === 'loading' && <Loading />}
      {state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
      {state.status === 'ok' && (
        <>
          {state.data.items.map((item) => (
            <CropCard key={item.crop} item={item} />
          ))}
          {state.data.not_available.length > 0 && (
            <p className="text-sm text-slate">
              {t('grow.notAvailable', { crops: state.data.not_available.map(cropName).join('، ') })}
            </p>
          )}
          <p className="text-xs text-slate">{t('grow.estimateNote')}</p>
          <DataLabel isSynthetic={state.data.is_synthetic} />
        </>
      )}
    </div>
  )
}

function CropCard({ item }: { item: CropPlanItem }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { cropName } = useAppState()
  const profit = item.expected_profit

  return (
    <article className="space-y-2 rounded-2xl bg-paper p-4 shadow-sm">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-lg font-bold">
          <span className="figures me-2 text-slate">{item.rank}</span>
          {cropName(item.crop)}
        </h3>
        <span className={`rounded px-2 text-sm ${RISK_STYLE[item.risk_level]}`}>
          {t('grow.risk')}: {t(`grow.riskLevels.${item.risk_level}`)}
        </span>
      </div>
      <p className="text-sm text-slate">{t('grow.profitTotal')}</p>
      <p className={`figures text-3xl ${profit >= 0 ? 'text-field' : 'text-madder'}`}>
        {profit >= 0 ? '+' : '−'}
        {formatRs(Math.abs(profit))}
      </p>
      <p className="text-sm text-slate">{t('grow.profitAcre', { amount: formatRs(item.profit_per_acre) })}</p>
      <p className="text-sm">
        {t('grow.harvestPrice', {
          price: formatRs(item.harvest_price_estimate),
          low: formatRs(item.harvest_price_low),
          high: formatRs(item.harvest_price_high),
        })}
      </p>
      {/* Cotton has no mandi price from March to June, so say which month's price the estimate starts from. */}
      <p className="text-xs text-slate">
        {t('grow.basedOn', { month: formatMonth(item.latest_price_date, lang), price: formatRs(item.latest_price) })}
      </p>
      <MonthStrip item={item} />
      <p className="text-sm">
        {item.best_sell_month == null || item.best_sell_gain_pct == null
          ? t('grow.noBestSell')
          : item.best_sell_gain_pct <= 0
            ? t('grow.sellAtHarvest', { month: t(`months.${item.best_sell_month}`) })
            : t('grow.bestSell', { month: t(`months.${item.best_sell_month}`), gain: item.best_sell_gain_pct.toFixed(1) })}
      </p>
      <p className="text-xs text-slate">
        {t('grow.years', { n: item.n_years })} ·{' '}
        <span className={item.is_stale ? 'font-semibold text-wheat-deep' : undefined}>
          {t(item.is_stale ? 'data.stale' : 'data.asOf', { date: formatDate(item.latest_price_date, lang) })}
        </span>
      </p>
    </article>
  )
}

/** Twelve months: sowing and harvest from the crop calendar, and the best month to sell. */
function MonthStrip({ item }: { item: CropPlanItem }) {
  const { t } = useTranslation()
  return (
    <div>
      <ol className="grid grid-cols-12 gap-0.5" aria-label={t('grow.sow') + ' / ' + t('grow.harvest')}>
        {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
          const sow = inSeason(m, item.sowing_months)
          const harvest = inSeason(m, item.harvest_months)
          const sell = item.best_sell_month === m
          const bg = sell ? 'bg-field' : harvest ? 'bg-wheat' : sow ? 'bg-ink/70' : 'bg-line'
          return (
            <li key={m} title={t(`months.${m}`)} className={`h-4 rounded-sm ${bg} ${sell ? 'ring-2 ring-field/40' : ''}`}>
              <span className="sr-only">{t(`months.${m}`)}</span>
            </li>
          )
        })}
      </ol>
      <ul className="mt-1 flex flex-wrap gap-x-3 text-xs text-slate">
        <li><span className="me-1 inline-block h-2.5 w-3 rounded-sm bg-ink/70 align-middle" />{t('grow.sow')}</li>
        <li><span className="me-1 inline-block h-2.5 w-3 rounded-sm bg-wheat align-middle" />{t('grow.harvest')}</li>
        <li><span className="me-1 inline-block h-2.5 w-3 rounded-sm bg-field align-middle" />{t('grow.sell')}</li>
      </ul>
    </div>
  )
}
