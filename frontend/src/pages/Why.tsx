import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { api, type ForecastResponse, type HoldHistory } from '../api/client'
import { useAppState } from '../appState'
import { DataLabel } from '../components/DataLabel'
import { DirectionLine } from '../components/DirectionLine'
import { SelectionBar } from '../components/SelectionBar'
import { ErrorBox, Loading } from '../components/Status'
import { Icon } from '../components/ui/Icon'
import type { Lang } from '../i18n'
import { addWeeks, formatMonth, formatNumber, formatRs } from '../lib/format'
import { CHART_MIN_TICK_GAP, CHART_TICK_PX, CHART_Y_AXIS_WIDTH, readTokens } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'

const ARROW = { UP: '⬆', DOWN: '⬇', '': '•' } as const

/** Plain reasons first; the price chart with the 4-week range sits behind "details" (blueprint UC-02). */
export function Why() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { selection } = useAppState()
  const key = `${selection.crop}|${selection.mandi}`
  const [explain, reloadExplain] = useAsync((signal) => api.explain(selection, signal), key)
  const [forecast] = useAsync((signal) => api.forecast(selection, signal), key)
  const [wait] = useAsync((signal) => api.waitPlan(selection, signal), key)

  return (
    <div className="space-y-6">
      <SelectionBar />
      <div className="space-y-6 lg:grid lg:grid-cols-2 lg:items-start lg:gap-6 lg:space-y-0">
      <section className="space-y-4 rounded-2xl border border-line bg-paper p-5 shadow-(--shadow-card) sm:p-6">
        <h2 className="flex items-center gap-2 text-2xl font-bold">
          <Icon name="why" className="size-6 text-field" />
          {t('why.title')}
        </h2>
        {explain.status === 'loading' && <Loading />}
        {explain.status === 'error' && <ErrorBox error={explain.error} onRetry={reloadExplain} />}
        {explain.status === 'ok' && (
          <>
            <DirectionLine direction={explain.data.direction} />
            <ul className="divide-y divide-line">
              {explain.data.reasons.map((r) => (
                <li key={r.text_en} className="flex gap-3 py-2.5 text-base">
                  <span aria-hidden className={r.direction === 'UP' ? 'text-field' : r.direction === 'DOWN' ? 'text-madder' : 'text-slate'}>
                    {ARROW[r.direction]}
                  </span>
                  <span>{lang === 'en' ? r.text_en : r.text_ur}</span>
                </li>
              ))}
            </ul>
            <p className="border-t border-line pt-3 text-sm text-slate">
              {explain.data.source === 'shap' ? t('why.sourceShap') : t('why.sourceFacts')}
            </p>
          </>
        )}
      </section>
      {wait.status === 'ok' && wait.data.history && wait.data.history.seasons.length > 0 && (
        <section className="space-y-3 rounded-2xl border border-line bg-paper p-5 shadow-(--shadow-card) sm:p-6">
          <h2 className="text-xl font-bold">{t('why.liquidityTitle')}</h2>
          <p className="text-sm text-slate">{t('why.liquidityNote', { months: wait.data.wait_months })}</p>
          <LiquidityChart history={wait.data.history} />
          <ul className="flex flex-wrap gap-x-4 text-xs text-slate">
            <li><span className="me-1 inline-block h-2.5 w-3 rounded-sm bg-field align-middle" />{t('why.legendPaid')}</li>
            <li><span className="me-1 inline-block h-2.5 w-3 rounded-sm bg-madder align-middle" />{t('why.legendLost')}</li>
          </ul>
        </section>
      )}
      </div>
      {forecast.status === 'ok' && (
        <details className="group rounded-2xl border border-line bg-paper p-5 shadow-(--shadow-card) sm:p-6">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 font-bold [&::-webkit-details-marker]:hidden">
            <span>{t('why.chart')}</span>
            <Icon name="chevron" className="size-5 text-field transition-transform group-open:rotate-180" />
          </summary>
          <ForecastChart f={forecast.data} lang={lang} />
        </details>
      )}
    </div>
  )
}

/** Each past year's outcome of holding (docs/PIVOT.md F2): the net gain per maund, green when holding paid. */
function LiquidityChart({ history }: { history: HoldHistory }) {
  const { t } = useTranslation()
  const c = useMemo(() => readTokens(), [])
  const data = history.seasons.map((s) => ({ year: String(s.year), net: s.net_gain_per_maund, paid: s.paid }))
  return (
    <>
      <div dir="ltr" className="h-56 w-full" role="img" aria-label={t('why.liquidityTitle')}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={c.line} vertical={false} />
            <XAxis dataKey="year" tick={{ fill: c.slate, fontSize: CHART_TICK_PX }} stroke={c.line} />
            <YAxis tickFormatter={(v: number) => formatNumber(v)} width={CHART_Y_AXIS_WIDTH}
              tick={{ fill: c.slate, fontSize: CHART_TICK_PX, fontFamily: 'IBM Plex Mono' }} stroke={c.line} />
            <Tooltip formatter={(v) => formatRs(Number(v))} />
            <Bar dataKey="net" name={t('why.liquidityTitle')} isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.year} fill={d.paid ? c.field : c.madder} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {data.some((d) => d.year === '2026') && <p className="text-xs text-wheat-deep">{t('why.capped')}</p>}
    </>
  )
}

function ForecastChart({ f, lang }: { f: ForecastResponse; lang: Lang }) {
  const { t } = useTranslation()
  const c = useMemo(() => readTokens(), [])
  const points = useMemo(() => {
    const p: { date: string; price?: number; band?: [number, number] }[] = f.history.map((h) => ({
      date: h.date,
      price: h.price ?? undefined, // a week without an AMIS price is a gap, never a joined line
    }))
    const last = p[p.length - 1]
    if (last) last.band = [last.price ?? f.current_price, last.price ?? f.current_price]
    p.push({ date: addWeeks(f.prices_as_of, f.horizon_weeks), band: [f.range.low, f.range.high] })
    return p
  }, [f])

  return (
    <div className="mt-3 space-y-2">
      {/* Time runs left to right in both languages, so the chart never mirrors. */}
      <div dir="ltr" className="h-60 w-full" role="img" aria-label={t('why.chart')}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={c.line} vertical={false} />
            <XAxis dataKey="date" tickFormatter={(d: string) => formatMonth(d, lang)} minTickGap={CHART_MIN_TICK_GAP}
              tick={{ fill: c.slate, fontSize: CHART_TICK_PX }} stroke={c.line} />
            <YAxis domain={['auto', 'auto']} tickFormatter={(v: number) => formatNumber(v)} width={CHART_Y_AXIS_WIDTH}
              tick={{ fill: c.slate, fontSize: CHART_TICK_PX, fontFamily: 'IBM Plex Mono' }} stroke={c.line} />
            <Tooltip formatter={(v) => (Array.isArray(v) ? v.map((x) => formatRs(Number(x))).join(' – ') : formatRs(Number(v)))} />
            <Area dataKey="band" name={t('why.legendRange')} stroke="none" fill={c.wheat} fillOpacity={0.35} isAnimationActive={false} />
            <Line dataKey="price" name={t('why.legendHistory')} stroke={c.ink} strokeWidth={2} dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <ul className="flex flex-wrap gap-x-4 text-xs text-slate">
        <li><span className="me-1 inline-block h-0.5 w-4 bg-ink align-middle" />{t('why.legendHistory')}</li>
        <li><span className="me-1 inline-block h-2.5 w-4 bg-wheat/35 align-middle" />{t('why.legendRange')}</li>
      </ul>
      <DataLabel isSynthetic={f.is_synthetic} asOf={f.prices_as_of} stale={f.is_stale} unchangedSince={f.price_unchanged_since} />
    </div>
  )
}
