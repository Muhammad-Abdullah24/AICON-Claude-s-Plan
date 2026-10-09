import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { api, type ForecastResponse } from '../api/client'
import { ChipGroup } from '../components/ChipGroup'
import { DataLabel } from '../components/DataLabel'
import { ErrorBox, Loading } from '../components/Status'
import type { Lang } from '../i18n'
import { addWeeks, formatMonth, formatNumber, formatRs } from '../lib/format'
import { readTokens } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'
import { useAppState } from '../appState'

interface Point {
  date: string
  price?: number
  q50?: number
  band?: [number, number]
  naive?: number
}

// Weeks of history drawn before the forecast. Two years would squeeze the 4-week fan into a
// sliver; six months keeps the forecast, the point of this screen, clearly visible.
const CHART_HISTORY_WEEKS = 26

/** Recent history, then the forecast fan. The last history point joins both so the lines connect. */
function toPoints(f: ForecastResponse): Point[] {
  const points: Point[] = f.history.slice(-CHART_HISTORY_WEEKS).map((h) => ({ date: h.date, price: h.price }))
  const last = points[points.length - 1]
  if (last) Object.assign(last, { q50: f.price_now, band: [f.price_now, f.price_now], naive: f.price_now })
  const naive = new Map(f.naive.map((n) => [n.weeks_ahead, n.price]))
  for (const b of f.forecast) {
    points.push({
      date: addWeeks(f.as_of, b.weeks_ahead),
      q50: b.q50,
      band: [b.q10, b.q90],
      naive: naive.get(b.weeks_ahead),
    })
  }
  return points
}

export function Forecast() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { meta, selection, setCrop, setMandi, mandisFor, name, cropName, mandiName } = useAppState()
  const [state, reload] = useAsync(
    (signal) => api.forecast({ crop: selection.crop, mandi: selection.mandi }, signal),
    `${selection.crop}|${selection.mandi}`,
  )

  return (
    <div className="space-y-5">
      <div className="space-y-4 rounded-2xl bg-paper p-4 shadow-sm">
        <ChipGroup
          label={t('ask.crop')}
          options={meta.crops.map((c) => ({ value: c.id, label: name(c) }))}
          value={selection.crop}
          onChange={setCrop}
        />
        <ChipGroup
          label={t('ask.mandi')}
          options={mandisFor(selection.crop).map((m) => ({ value: m.id, label: name(m) }))}
          value={selection.mandi}
          onChange={setMandi}
        />
      </div>

      {state.status === 'loading' && <Loading />}
      {state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
      {state.status === 'ok' && (
        <ForecastView
          f={state.data}
          lang={lang}
          title={t('forecast.chartLabel', { crop: cropName(state.data.crop), mandi: mandiName(state.data.mandi) })}
        />
      )}
    </div>
  )
}

function ForecastView({ f, lang, title }: { f: ForecastResponse; lang: Lang; title: string }) {
  const { t } = useTranslation()
  const points = useMemo(() => toPoints(f), [f])
  const c = useMemo(() => readTokens(), [])

  return (
    <section className="space-y-4 rounded-2xl bg-paper p-4 shadow-sm" aria-label={title}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm text-slate">{t('forecast.today')}</span>
        <span className="figures text-3xl font-medium">{formatRs(f.price_now)}</span>
      </div>

      {/* Time runs left to right in both languages, so the chart never mirrors. */}
      <div dir="ltr" className="h-64 w-full" role="img" aria-label={title}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke={c.line} vertical={false} />
            <XAxis
              dataKey="date"
              tickFormatter={(d: string) => formatMonth(d, lang)}
              minTickGap={40}
              tick={{ fill: c.slate, fontSize: 12 }}
              stroke={c.line}
            />
            <YAxis
              domain={['auto', 'auto']}
              tickFormatter={(v: number) => formatNumber(v)}
              width={56}
              tick={{ fill: c.slate, fontSize: 12, fontFamily: 'IBM Plex Mono' }}
              stroke={c.line}
            />
            <Tooltip
              formatter={(v) => (Array.isArray(v) ? v.map((x) => formatRs(Number(x))).join(' – ') : formatRs(Number(v)))}
              labelFormatter={(d) => String(d)}
            />
            <Area dataKey="band" name={t('forecast.legendBand')} stroke="none" fill={c.wheat} fillOpacity={0.35} isAnimationActive={false} />
            <Line dataKey="price" name={t('forecast.legendHistory')} stroke={c.ink} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="q50" name={t('forecast.legendMedian')} stroke={c.wheat} strokeWidth={2.5} dot={false} isAnimationActive={false} />
            <Line dataKey="naive" name={t('forecast.legendNaive')} stroke={c.slate} strokeDasharray="5 4" strokeWidth={1.5} dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate">
        <li><span className="me-1 inline-block h-0.5 w-4 bg-ink align-middle" />{t('forecast.legendHistory')}</li>
        <li><span className="me-1 inline-block h-0.5 w-4 bg-wheat align-middle" />{t('forecast.legendMedian')}</li>
        <li><span className="me-1 inline-block h-2.5 w-4 bg-wheat/35 align-middle" />{t('forecast.legendBand')}</li>
        <li><span className="me-1 inline-block w-4 border-t-2 border-dashed border-slate align-middle" />{t('forecast.legendNaive')}</li>
      </ul>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate">
            <th className="py-1 text-start font-normal" />
            <th className="py-1 text-end font-normal">{t('forecast.range')}</th>
          </tr>
        </thead>
        <tbody>
          {f.forecast.map((b) => (
            <tr key={b.weeks_ahead} className="border-t border-line">
              <td className="py-1.5">{t('forecast.weeksAhead', { count: b.weeks_ahead })}</td>
              <td className="figures py-1.5 text-end">
                {formatRs(b.q10)} – {formatRs(b.q90)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <dl className="grid grid-cols-[auto_1fr] gap-x-3 text-xs text-slate">
        <dt>{t('forecast.model')}</dt>
        <dd lang="en" dir="ltr" className="text-end">{f.model}</dd>
        <dt>{t('forecast.accuracy')}</dt>
        <dd className="text-end">
          {f.mase_vs_naive == null ? t('forecast.notMeasured') : <span className="figures">MASE {f.mase_vs_naive.toFixed(2)}</span>}
        </dd>
      </dl>

      <DataLabel isSynthetic={f.is_synthetic} priceType={f.price_type} asOf={f.as_of} />
    </section>
  )
}
