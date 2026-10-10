import { AlertTriangle, Calendar, CheckCircle2, Clock, MapPin, Phone } from 'lucide-react'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { api, type ForecastResponse } from '../api/client'
import { useAppState } from '../appState'
import { DataLabel } from '../components/DataLabel'
import { DirectionLine } from '../components/DirectionLine'
import { CannotKnow } from '../components/OfferResult'
import { SelectionBar } from '../components/SelectionBar'
import { ErrorBox, Loading } from '../components/Status'
import { ButtonLink } from '../components/ui/Button'
import { Note } from '../components/ui/Disclosure'
import { StatusBadge } from '../components/ui/StatusBadge'
import type { Lang } from '../i18n'
import { addWeeks, formatDate, formatMonth, formatNumber, formatRs } from '../lib/format'
import { referenceBadge } from '../lib/status'
import { CHART_MIN_TICK_GAP, CHART_TICK_PX, CHART_Y_AXIS_WIDTH, readTokens } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'

const ARROW = { UP: '⬆', DOWN: '⬇', '': '•' } as const

/** How strong the reference is, in the "reference data is limited" layout when it is weak. */
function ReferenceQuality() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { selection, cropName, mandiName } = useAppState()
  const [ref, reload] = useAsync((signal) => api.reference(selection, signal), `${selection.crop}|${selection.mandi}`)
  if (ref.status === 'loading') return <Loading label={t('home.reference.loading')} />
  if (ref.status === 'error') return <ErrorBox error={ref.error} onRetry={reload} />
  const r = ref.data
  const strong = r.reference_strength === 'STRONG'
  const when = formatDate(r.price_unchanged_since ?? r.reference_price_as_of, lang)
  const Icon = r.reference_strength === 'LIMITED_STALE' ? Clock : strong ? CheckCircle2 : AlertTriangle
  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold lg:text-3xl">{t(strong ? 'details.titleStrong' : 'details.titleLimited')}</h1>
        <p className="text-slate">
          {cropName(r.crop)} · {mandiName(r.mandi)} ·{' '}
          {t('details.reviewed', { date: formatDate(r.reference_price_as_of, lang) })}
        </p>
      </header>
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <section
            className={`space-y-3 rounded-[var(--radius-card)] border p-5 lg:p-6 ${
              strong ? 'border-line bg-paper' : 'border-wheat/50 bg-wheat-soft'
            }`}
            data-testid="reference-quality"
          >
            <p className={`flex items-start gap-2 text-lg font-semibold ${strong ? 'text-field' : 'text-wheat-deep'}`}>
              <Icon aria-hidden className="mt-1 size-6 shrink-0" />
              {strong
                ? t('details.strongHeadline')
                : t(`offer.limited.${r.reference_strength}`, { days: r.reference_days, window: r.window_days, date: when })}
            </p>
            <p className="text-sm">{t('details.availableReference')}</p>
            <p className="figures text-4xl">{formatRs(r.reference_price)}</p>
            <DataLabel
              isSynthetic={r.is_synthetic}
              asOf={r.reference_price_as_of}
              stale={r.is_stale}
              unchangedSince={r.price_unchanged_since}
            />
            <StatusBadge kind={referenceBadge(r)} />
            <p className={`text-sm ${strong ? 'text-slate' : 'text-wheat-deep'}`}>
              {t(strong ? 'details.strongExplain' : 'details.limitedExplain')}
            </p>
          </section>
          <Note>
            {t('offer.reportedDays', { days: r.reference_days, window: r.window_days })}{' '}
            {t('details.range', { low: formatRs(r.reference_range_low), high: formatRs(r.reference_range_high) })}
          </Note>
          <CannotKnow open />
        </div>
        <aside className="space-y-4">
          <section className="card space-y-3 p-5">
            <h2 className="text-lg font-semibold">{t('offer.whatYouCanDo.title')}</h2>
            <p className="text-sm text-slate">{t('offer.whatYouCanDo.body')}</p>
            <ButtonLink to="/compare" wide>
              <MapPin aria-hidden className="size-5" />
              {t('offer.whatYouCanDo.tryMandi')}
            </ButtonLink>
            <ButtonLink to="/history" variant="secondary" wide>
              <Calendar aria-hidden className="size-5" />
              {t('details.seeHistory')}
            </ButtonLink>
            <p className="flex items-center justify-center gap-2 py-2 text-center text-field">
              <Phone aria-hidden className="size-5 shrink-0" />
              {t('offer.whatYouCanDo.askMandi')}
            </p>
          </section>
          <Note tone="caution">{t('offer.checkYourself')}</Note>
        </aside>
      </div>
    </div>
  )
}

/**
 * Data details: first how strong the AMIS reference is (stale, frozen, one repeated price, too few days), then
 * the model's reasons and the price chart as background (market outlook context, never the offer's answer).
 */
export function Why() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { selection } = useAppState()
  const key = `${selection.crop}|${selection.mandi}`
  const [explain, reloadExplain] = useAsync((signal) => api.explain(selection, signal), key)
  const [forecast] = useAsync((signal) => api.forecast(selection, signal), key)

  return (
    <div className="space-y-6">
      <SelectionBar />
      <ReferenceQuality />
      <section className="card space-y-3 p-5" aria-labelledby="why-title">
        <h2 id="why-title" className="text-xl font-bold">
          {t('why.title')}
        </h2>
        <p className="text-sm text-slate">{t('outlook.context')}</p>
        {explain.status === 'loading' && <Loading />}
        {explain.status === 'error' && <ErrorBox error={explain.error} onRetry={reloadExplain} />}
        {explain.status === 'ok' && (
          <>
            <DirectionLine direction={explain.data.direction} />
            <ul className="space-y-2">
              {explain.data.reasons.map((r) => (
                <li key={r.text_en} className="flex gap-2 text-base">
                  <span
                    aria-hidden
                    className={r.direction === 'UP' ? 'text-field' : r.direction === 'DOWN' ? 'text-madder' : 'text-slate'}
                  >
                    {ARROW[r.direction]}
                  </span>
                  <span>{lang === 'en' ? r.text_en : r.text_ur}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate">
              {explain.data.source === 'shap' ? t('why.sourceShap') : t('why.sourceFacts')}
            </p>
          </>
        )}
      </section>
      {forecast.status === 'ok' && (
        <details className="card p-5">
          <summary className="min-h-12 cursor-pointer py-2 font-bold">{t('why.chart')}</summary>
          <ForecastChart f={forecast.data} lang={lang} />
        </details>
      )}
    </div>
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
              tick={{ fill: c.slate, fontSize: CHART_TICK_PX, fontFamily: 'IBM Plex Sans' }} stroke={c.line} />
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
