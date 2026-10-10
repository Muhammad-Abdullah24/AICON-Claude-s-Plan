import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, type CropPlanItem, type CropPlanResponse } from '../api/client'
import { useAppState } from '../appState'
import { ChipGroup } from '../components/ChipGroup'
import { HelpTip } from '../components/HelpTip'
import { DataLabel } from '../components/DataLabel'
import { ErrorBox, Loading } from '../components/Status'
import type { Lang } from '../i18n'
import { formatDate, formatMonth, formatRs, parseTypedNumber } from '../lib/format'
import { inSeason } from '../lib/months'
import { useAsync } from '../lib/useAsync'
import {
  bestPick,
  noteLine,
  notRankedKeys,
  policyLine,
  seasonSections,
  seasonStatusLine,
  type SeasonSection,
  type SupportPriceContext,
} from './growLogic'

const RISK_STYLE = { LOW: 'bg-field text-paper', MEDIUM: 'bg-wheat text-ink', HIGH: 'bg-madder text-paper' } as const

/**
 * Crop options with their expected profit at harvest, season and best selling month (UC-05, UC-06), compared only
 * within a season and only on current, reliable reference prices (F4). The API decides which crops are ranked.
 */
export function Grow() {
  const { t } = useTranslation()
  const { meta, farmer, name, cropName } = useAppState()
  // Default: the farmer's district, else the first mandi the API lists (never a hardcoded mandi).
  const [mandi, setMandi] = useState<string>(farmer?.district ?? meta.mandis[0].id)
  const [landTyped, setLandTyped] = useState(String(farmer?.land_area_acres ?? 10))
  const land = parseTypedNumber(landTyped)
  const acres = land !== null && land > 0 ? land : undefined
  const [state, reload] = useAsync(
    (signal) => api.cropPlan({ mandi, land_area_acres: acres }, signal),
    `${mandi}|${acres ?? ''}`,
  )

  return (
    <div className="space-y-5">
      {/* One line until tapped, so the ranking stays on the first screen (same pattern as SelectionBar). */}
      <details className="group rounded-2xl bg-paper shadow-sm">
        <summary
          onClick={(e) => acres === undefined && e.preventDefault()}
          className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 py-2 [&::-webkit-details-marker]:hidden"
        >
          <span className="font-bold">
            {name(meta.mandis.find((m) => m.id === mandi))} · {acres ?? '–'} {t('grow.acres')}
          </span>
          <span className="shrink-0 rounded-full border-2 border-line px-3 text-sm text-slate group-open:hidden">
            {t('select.change')}
          </span>
          <span className="hidden shrink-0 rounded-full border-2 border-line px-3 text-sm text-slate group-open:inline">
            {t('select.done')}
          </span>
        </summary>
        <div className="space-y-4 px-4 pb-4">
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
                aria-invalid={acres === undefined}
                aria-describedby={acres === undefined ? 'land-error' : undefined}
                className="figures min-h-12 w-28 rounded-xl border-2 border-line bg-paper px-3 py-2 text-xl focus:border-ink focus:outline-none"
              />
              <span>{t('grow.acres')}</span>
            </div>
            {acres === undefined && (
              <p id="land-error" className="mt-1 text-sm text-madder">{t('grow.landInvalid')}</p>
            )}
          </div>
        </div>
      </details>

      <h2 className="text-xl font-bold">
        {t('grow.title')}
        <HelpTip text={t('help.grow')} />
      </h2>
      {state.status === 'loading' && <Loading />}
      {state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
      {state.status === 'ok' && <BestPick plan={state.data} />}
      {state.status === 'ok' && (
        <>
          {seasonSections(state.data).map((section) => (
            <SeasonBlock
              key={section.season}
              section={section}
              policy={section.items.some((i) => i.crop === 'wheat') ? state.data.support_price_context : null}
            />
          ))}
          {state.data.not_available.length > 0 && (
            <p className="text-sm text-slate">
              {t('grow.notAvailable', { crops: state.data.not_available.map(cropName).join('، ') })}
            </p>
          )}
          <DataLabel isSynthetic={state.data.is_synthetic} />
        </>
      )}
    </div>
  )
}

/** The headline recommendation: the highest-profit ranked crop, stated plainly. Nothing when nothing ranked, so
 * the app never shows a headline pick it is not confident in (stale or thin-history crops are left to their cards). */
function BestPick({ plan }: { plan: CropPlanResponse }) {
  const { t } = useTranslation()
  const { cropName } = useAppState()
  const best = bestPick(plan)
  if (!best) return null
  return (
    <aside className="space-y-1 rounded-2xl border-2 border-field bg-field/10 p-4">
      <p className="text-sm font-semibold text-field">{t('grow.bestPick.title')}</p>
      <p className="text-2xl font-bold">{cropName(best.crop)}</p>
      <p className="figures text-2xl text-field">
        +{formatRs(best.profit_per_acre)} <span className="text-base text-slate">/ {t('grow.acres')}</span>
      </p>
      <p className="text-sm text-slate">
        {t('grow.bestPick.line', { risk: t(`grow.riskLevels.${best.risk_level}`) })}
      </p>
    </aside>
  )
}

/** One season: whether its crops could be compared (and why not), the wheat policy context, then the crops. */
function SeasonBlock({ section, policy }: { section: SeasonSection; policy: SupportPriceContext | null }) {
  const { t } = useTranslation()
  const status = seasonStatusLine(section)
  const headingId = `season-${section.season}`
  return (
    <section className="space-y-3" aria-labelledby={headingId}>
      <h3 id={headingId} className="text-lg font-bold">
        {t(`grow.seasons.${section.season}`)}
      </h3>
      <p
        role="status"
        className={`rounded-xl p-3 text-sm ${section.status === 'RANKED' ? 'bg-paper text-slate' : 'bg-wheat-soft text-ink'}`}
      >
        {t(status.key, status.params)}
      </p>
      {policy && <PolicyContext ctx={policy} />}
      {section.items.map((item) => (
        <CropCard key={item.crop} item={item} />
      ))}
    </section>
  )
}

/** Wheat's support-price status from the policy timeline (H3): context, never a mandi price or a promise. */
function PolicyContext({ ctx }: { ctx: SupportPriceContext }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const line = policyLine(ctx, lang, (iso) => formatDate(iso, lang))
  return (
    <aside className="space-y-1 rounded-2xl border-2 border-line bg-paper p-4">
      <h4 className="font-bold">{t('grow.policy.title')}</h4>
      <p className={ctx.state === 'CURRENT' ? undefined : 'text-wheat-deep'}>{t(line.key, line.params)}</p>
      {ctx.uncertain && (
        <p className="text-wheat-deep">{t('grow.policy.uncertain', { days: ctx.uncertain_window_days })}</p>
      )}
      <p className="text-sm text-slate">{t('grow.policy.limit')}</p>
      {ctx.event && (
        <a href={ctx.event.url} target="_blank" rel="noreferrer" className="inline-flex min-h-12 items-center text-sm underline">
          {t('grow.policy.link')}
        </a>
      )}
    </aside>
  )
}

function CropCard({ item }: { item: CropPlanItem }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { cropName } = useAppState()
  const profit = item.expected_profit
  const notRanked = notRankedKeys(item)

  return (
    <article className="space-y-2 rounded-2xl bg-paper p-4 shadow-sm">
      <div className="flex items-baseline justify-between gap-3">
        <h4 className="text-lg font-bold">
          {item.rank != null && <span className="figures me-2 text-slate">{item.rank}</span>}
          {cropName(item.crop)}
        </h4>
        <span className={`rounded px-2 text-sm ${RISK_STYLE[item.risk_level]}`}>
          {t('grow.risk')}: {t(`grow.riskLevels.${item.risk_level}`)}
        </span>
      </div>
      {notRanked && notRanked.length > 0 && (
        <p className="text-sm text-wheat-deep">
          {t('grow.notRanked')} {notRanked.map((k) => t(k)).join('، ')}
        </p>
      )}
      <p className="text-sm text-slate">{t('grow.profitTotal')}</p>
      <p className={`figures text-3xl ${profit >= 0 ? 'text-field' : 'text-madder'}`}>
        {profit >= 0 ? '+' : '−'}
        {formatRs(Math.abs(profit))}
      </p>
      <p className="text-sm text-slate">
        {t('grow.profitAcre', { amount: formatRs(item.profit_per_acre) })}{' '}
        {t('grow.profitRange', { low: formatRs(item.profit_per_acre_low), high: formatRs(item.profit_per_acre_high) })}
      </p>
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
          : item.sell_at_harvest
            ? t('grow.sellAtHarvest', { month: t(`months.${item.best_sell_month}`) })
            : t('grow.bestSell', { month: t(`months.${item.best_sell_month}`), gain: item.best_sell_gain_pct.toFixed(1) })}
      </p>
      <p className="text-xs text-slate">
        {t('grow.years', { n: item.n_years })} ·{' '}
        <span className={item.is_stale ? 'font-semibold text-wheat-deep' : undefined}>
          {t(item.is_stale ? 'data.stale' : 'data.asOf', { date: formatDate(item.latest_price_date, lang) })}
        </span>
      </p>
      {item.notes.map((note) => {
        const line = noteLine(note, item, (m) => t(`months.${m}`), (iso) => formatDate(iso, lang))
        return (
          <p key={note.id} className="rounded-xl bg-wheat-soft p-3 text-sm">
            {t(line.key, line.params)}{' '}
            <a href={note.url} target="_blank" rel="noreferrer" className="inline-flex min-h-12 min-w-12 items-center justify-center px-1 underline">
              {t('grow.noteSource')}
            </a>
          </p>
        )
      })}
    </article>
  )
}

/** Twelve months: sowing and harvest from the crop calendar, and the selling window (the best month ringed). */
function MonthStrip({ item }: { item: CropPlanItem }) {
  const { t } = useTranslation()
  return (
    <div>
      <ol className="grid grid-cols-12 gap-0.5" aria-label={t('grow.sow') + ' / ' + t('grow.harvest')}>
        {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
          const sow = inSeason(m, item.sowing_months)
          const harvest = inSeason(m, item.harvest_months)
          const sell = item.sell_window_months.includes(m)
          const best = item.best_sell_month === m
          const bg = sell ? 'bg-field' : harvest ? 'bg-wheat' : sow ? 'bg-ink/70' : 'bg-line'
          return (
            <li key={m} title={t(`months.${m}`)} className={`h-4 rounded-sm ${bg} ${best ? 'ring-2 ring-field/40' : ''}`}>
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
