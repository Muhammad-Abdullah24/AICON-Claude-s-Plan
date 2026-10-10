import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import { useAsync } from '../lib/useAsync'
import { Icon } from './ui/Icon'

/** This week's weather at the mandi, with the credit Open-Meteo's CC BY 4.0 licence requires. */
export function WeatherLine({ mandi }: { mandi: string }) {
  const { t } = useTranslation()
  const [state] = useAsync((signal) => api.weather(mandi, signal), mandi)
  if (state.status !== 'ok') return null
  const w = state.data.weather
  return (
    <p className="flex flex-wrap items-center gap-x-2 rounded-2xl border border-line bg-paper px-4 py-1 text-sm text-slate">
      <Icon name="info" className="size-5 text-slate" />
      <span>
        {t('data.weatherLine', {
          tmax: w.tmax_c == null ? '–' : Math.round(w.tmax_c),
          rain: w.precip_mm_wk == null ? '–' : Math.round(w.precip_mm_wk),
        })}
      </span>
      {w.cached && <span>{t('data.weatherCached')}</span>}
      <a href="https://open-meteo.com/" target="_blank" rel="noreferrer" className="inline-flex min-h-12 items-center underline">
        {t('data.weatherCredit')}
      </a>
    </p>
  )
}
