import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { api } from '../api/client'
import { useAppState } from '../appState'
import { OfferCheck } from '../components/OfferCheck'
import { SelectionBar } from '../components/SelectionBar'
import { SignalCard } from '../components/SignalCard'
import { ErrorBox, Loading } from '../components/Status'
import { WeatherLine } from '../components/WeatherLine'
import { useAsync } from '../lib/useAsync'

/** Answer first (blueprint section 11): the SELL / WAIT card, then the four big actions. */
export function Home() {
  const { t } = useTranslation()
  const { selection, quantity } = useAppState()
  const [advice, reload] = useAsync(
    (signal) => api.advice({ ...selection, quantity_maund: quantity }, signal),
    `${selection.crop}|${selection.mandi}|${quantity}`,
  )

  const actions = [
    { to: '/why', label: t('actions.why') },
    { to: '/compare', label: t('actions.compare') },
    { to: '/grow', label: t('actions.grow') },
    { to: '/chat', label: t('actions.ask') },
  ]

  return (
    <div className="space-y-5">
      <SelectionBar withQuantity />
      {advice.status === 'loading' && <Loading />}
      {advice.status === 'error' && <ErrorBox error={advice.error} onRetry={reload} />}
      {advice.status === 'ok' && <SignalCard advice={advice.data} />}
      <WeatherLine mandi={selection.mandi} />
      <nav className="grid grid-cols-2 gap-3" aria-label={t('app.name')}>
        {actions.map((a) => (
          <Link
            key={a.to}
            to={a.to}
            className="flex min-h-14 items-center justify-center rounded-2xl bg-ink px-3 py-3 text-center text-lg font-bold text-cotton hover:opacity-90"
          >
            {a.label}
          </Link>
        ))}
      </nav>
      <OfferCheck />
    </div>
  )
}
