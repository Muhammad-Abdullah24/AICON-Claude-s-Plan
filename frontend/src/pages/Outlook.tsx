import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { api } from '../api/client'
import { useAppState } from '../appState'
import { SelectionBar } from '../components/SelectionBar'
import { MORE } from '../components/shell/nav'
import { SignalCard } from '../components/SignalCard'
import { ErrorBox, Loading } from '../components/Status'
import { Note } from '../components/ui/Disclosure'
import { WeatherLine } from '../components/WeatherLine'
import { useAsync } from '../lib/useAsync'

/**
 * Market outlook: the price estimate, its range, the model's direction call and the weather, as background.
 * Secondary to the offer check: forecasts were tested and are not reliable enough to tell a farmer to hold.
 */
export function Outlook() {
  const { t } = useTranslation()
  const { selection, quantity } = useAppState()
  const [advice, reload] = useAsync(
    (signal) => api.advice({ ...selection, quantity_maund: quantity }, signal),
    `${selection.crop}|${selection.mandi}|${quantity}`,
  )

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold lg:text-3xl">{t('outlook.title')}</h1>
        <p className="text-sm text-slate">{t('outlook.note')}</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <SelectionBar withQuantity />
          {advice.status === 'loading' && <Loading />}
          {advice.status === 'error' && <ErrorBox error={advice.error} onRetry={reload} />}
          {advice.status === 'ok' && <SignalCard advice={advice.data} secondary />}
          <WeatherLine mandi={selection.mandi} />
        </div>
        <div className="space-y-4">
          <Note>{t('outlook.context')}</Note>
          <Link to="/why" className="card block p-5 font-semibold text-field hover:bg-field-soft">
            {t('outlook.whyLink')}
          </Link>
          <nav className="card space-y-1 p-5 lg:hidden" aria-label={t('nav.more')}>
            <p className="text-sm font-semibold text-slate">{t('nav.more')}</p>
            {MORE.map(({ to, key }) => (
              <Link key={to} to={to} className="block min-h-11 py-2 text-field">
                {t(`nav.${key}`)}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </div>
  )
}
