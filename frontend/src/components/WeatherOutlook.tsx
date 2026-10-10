import { useTranslation } from 'react-i18next'

import { api, type WeatherOutlookResponse } from '../api/client'
import type { Lang } from '../i18n'
import { useAsync } from '../lib/useAsync'

const RAIN_MM = 1
const RAIN_PROB = 30

/** "13 October": day and month, no year (the forecast is always the next two weeks). */
function shortDate(iso: string, t: (k: string) => string): string {
  return `${Number(iso.slice(8, 10))} ${t(`months.${Number(iso.slice(5, 7))}`)}`
}

/** "Today", "Tomorrow" or the weekday, so a farmer reads when, not a date. */
function dayName(iso: string, lang: Lang, t: (k: string) => string): string {
  const d = new Date(`${iso}T12:00:00`)
  const today = new Date()
  today.setHours(12, 0, 0, 0)
  const diff = Math.round((d.getTime() - today.getTime()) / 86_400_000)
  if (diff === 0) return t('outlook.today')
  if (diff === 1) return t('outlook.tomorrow')
  return d.toLocaleDateString(lang === 'ur' ? 'ur-PK' : 'en-GB', { weekday: 'long' })
}

/**
 * The rain outlook at the mandi, in one plain line and a 7-day strip of icons (Open-Meteo's daily forecast, up to
 * 16 days). Hidden if the forecast is unavailable, so it never shows an error on Home.
 */
export function WeatherOutlook({ mandi }: { mandi: string }) {
  const { t, i18n } = useTranslation()
  const lang = i18n.language as Lang
  const [state] = useAsync((signal) => api.weatherOutlook(mandi, signal), `outlook|${mandi}`)
  if (state.status !== 'ok') return null
  const o: WeatherOutlookResponse = state.data
  const rainy = o.headline !== 'DRY'
  const headline =
    o.headline === 'RAIN_SOON'
      ? t('outlook.rainSoon', { day: dayName(o.first_rain_date!, lang, t), prob: o.first_rain_prob })
      : o.headline === 'RAIN_LATER'
        ? t('outlook.rainLater', { date: shortDate(o.first_rain_date!, t) })
        : t('outlook.dry', { days: o.horizon_days })
  const dryAfter =
    rainy && o.dry_from && o.dry_days >= 5
      ? t('outlook.dryAfter', { date: shortDate(o.dry_from, t), days: o.dry_days })
      : null

  return (
    <section className="space-y-3 rounded-2xl border border-line bg-paper p-4" aria-label={t('outlook.title')}>
      <p className="flex items-center gap-3 text-xl font-bold">
        <span aria-hidden className="text-3xl">
          {o.headline === 'RAIN_SOON' ? '🌧️' : '☀️'}
        </span>
        <span>{headline}</span>
      </p>
      {dryAfter && <p className="text-base">☀️ {dryAfter}</p>}
      {o.max_temp_7d >= 40 && <p className="text-base">🔥 {t('outlook.hot', { t: o.max_temp_7d })}</p>}
      <ol className="grid grid-cols-7 gap-1 text-center" dir="ltr">
        {o.days.map((d) => {
          const wet = d.rain_mm >= RAIN_MM && d.rain_prob >= RAIN_PROB
          return (
            <li key={d.date} className={`rounded-xl py-1 ${wet ? 'bg-field-soft' : ''}`}>
              <span className="figures block text-sm text-slate">{Number(d.date.slice(8, 10))}</span>
              <span aria-hidden className="block text-xl">
                {wet ? '🌧️' : '☀️'}
              </span>
              <span className="figures block text-sm">{d.tmax == null ? '–' : `${d.tmax}°`}</span>
            </li>
          )
        })}
      </ol>
      <a
        href="https://open-meteo.com/"
        target="_blank"
        rel="noreferrer"
        className="inline-flex min-h-12 items-center text-sm text-slate underline"
      >
        {t('data.weatherCredit')}
      </a>
    </section>
  )
}
