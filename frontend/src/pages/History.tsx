import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { api } from '../api/client'
import { useAppState } from '../appState'
import { DataLabel } from '../components/DataLabel'
import { SelectionBar } from '../components/SelectionBar'
import { ErrorBox, Loading } from '../components/Status'
import type { Lang } from '../i18n'
import { formatMonth, formatNumber, formatRs } from '../lib/format'
import { inSeason } from '../lib/months'
import { CHART_MIN_TICK_GAP, CHART_TICK_PX, CHART_Y_AXIS_WIDTH, readTokens } from '../lib/tokens'
import { useAsync } from '../lib/useAsync'

/** 52 weeks of prices, and the usual price by month as % of the yearly trend (UC-12). */
export function History() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const { selection } = useAppState()
  const [state, reload] = useAsync((signal) => api.history(selection, signal), `${selection.crop}|${selection.mandi}`)
  const c = useMemo(() => readTokens(), [])

  return (
    <div className="space-y-6">
      <SelectionBar />
      {state.status === 'loading' && <Loading />}
      {state.status === 'error' && <ErrorBox error={state.error} onRetry={reload} />}
      {state.status === 'ok' && (
        <>
          <section className="space-y-3 rounded-2xl border border-line bg-paper p-5 shadow-(--shadow-card) sm:p-6">
            <h2 className="text-xl font-bold">{t('history.weekly')}</h2>
            <div dir="ltr" className="h-56 w-full" role="img" aria-label={t('history.weekly')}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={state.data.weekly} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={c.line} vertical={false} />
                  <XAxis dataKey="date" tickFormatter={(d: string) => formatMonth(d, lang)} minTickGap={CHART_MIN_TICK_GAP}
                    tick={{ fill: c.slate, fontSize: CHART_TICK_PX }} stroke={c.line} />
                  <YAxis domain={['auto', 'auto']} tickFormatter={(v: number) => formatNumber(v)} width={CHART_Y_AXIS_WIDTH}
                    tick={{ fill: c.slate, fontSize: CHART_TICK_PX, fontFamily: 'IBM Plex Mono' }} stroke={c.line} />
                  <Tooltip formatter={(v) => formatRs(Number(v))} />
                  <Line dataKey="price" stroke={c.ink} strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <DataLabel isSynthetic={state.data.is_synthetic} asOf={state.data.prices_as_of} />
          </section>

          <section className="space-y-3 rounded-2xl border border-line bg-paper p-5 shadow-(--shadow-card) sm:p-6">
            <h2 className="text-xl font-bold">{t('history.seasonal')}</h2>
            <div dir="ltr" className="h-52 w-full" role="img" aria-label={t('history.seasonal')}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={state.data.seasonal} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={c.line} vertical={false} />
                  {/* Urdu month names are never cut short (a 3-letter Urdu fragment is not a word): full names,
                      every third month. English uses the short form, every other month. */}
                  <XAxis dataKey="month"
                    tickFormatter={(m: number) => (lang === 'ur' ? t(`months.${m}`) : t(`months.${m}`).slice(0, 3))}
                    tick={{ fill: c.slate, fontSize: CHART_TICK_PX }} stroke={c.line} interval={lang === 'ur' ? 2 : 1} />
                  <YAxis domain={[80, 120]} width={48} tick={{ fill: c.slate, fontSize: CHART_TICK_PX }}
                    stroke={c.line} />
                  <ReferenceLine y={100} stroke={c.slate} strokeDasharray="4 3" />
                  <Tooltip formatter={(v) => (v == null ? '–' : `${Number(v).toFixed(0)}%`)}
                    labelFormatter={(m) => t(`months.${String(m)}`)} />
                  <Bar dataKey="index_median" isAnimationActive={false}>
                    {state.data.seasonal.map((s) => (
                      <Cell key={s.month}
                        fill={inSeason(s.month, state.data.harvest_months) ? c.wheat : inSeason(s.month, state.data.sowing_months) ? c.ink : c.slate} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <ul className="flex flex-wrap gap-x-3 text-xs text-slate">
              <li><span className="me-1 inline-block h-2.5 w-3 rounded-sm bg-ink align-middle" />{t('history.sowing')}</li>
              <li><span className="me-1 inline-block h-2.5 w-3 rounded-sm bg-wheat align-middle" />{t('history.harvest')}</li>
            </ul>
            <p className="text-xs text-slate">{t('history.seasonalNote')}</p>
          </section>
        </>
      )}
    </div>
  )
}
