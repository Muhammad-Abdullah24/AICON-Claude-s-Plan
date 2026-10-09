import { useTranslation } from 'react-i18next'

import { api } from '../api/client'
import { useAsync } from '../lib/useAsync'

/** This week's weather at the mandi, with the credit Open-Meteo's CC BY 4.0 licence requires. */
export function WeatherLine({ mandi }: { mandi: string }) {
  const { t } = useTranslation()
  const [state] = useAsync((signal) => api.weather(mandi, signal), mandi)
  if (state.status !== 'ok') return null
  const w = state.data.weather
  return (
    <p className="flex flex-wrap gap-x-2 text-xs text-slate">
      <span>
        {t('data.weatherLine', {
          tmax: w.tmax_c == null ? '–' : Math.round(w.tmax_c),
          rain: w.precip_mm_wk == null ? '–' : Math.round(w.precip_mm_wk),
        })}
      </span>
      {w.cached && <span>{t('data.weatherCached')}</span>}
      <a href="https://open-meteo.com/" target="_blank" rel="noreferrer" className="underline">
        {t('data.weatherCredit')}
      </a>
    </p>
  )
}
