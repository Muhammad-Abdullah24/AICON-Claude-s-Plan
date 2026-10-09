import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { api } from '../api/client'
import { useAppState } from '../appState'
import { OfferCheck } from '../components/OfferCheck'
import { SignalCard } from '../components/SignalCard'
import { ErrorBox, Loading } from '../components/Status'
import { WeatherLine } from '../components/WeatherLine'
import { useAsync } from '../lib/useAsync'

/**
 * Check a buyer's offer first: that is the decision a farmer faces at the gate. The market outlook (the price
 * estimate, the model's direction call and the sell/wait card) follows as secondary context, then the actions.
 */
export function Home() {
  const { t } = useTranslation()
  const { selection, quantity } = useAppState()
  const [advice, reload] = useAsync(
    (signal) => api.advice({ ...selection, quantity_maund: quantity }, signal),
    `${selection.crop}|${selection.mandi}|${quantity}`,
  )

  const actions = [
    { to: '/compare', label: t('actions.compare') },
    { to: '/why', label: t('actions.why') },
    { to: '/grow', label: t('actions.grow') },
    { to: '/chat', label: t('actions.ask') },
  ]

  return (
    <div className="space-y-6">
      <OfferCheck />

      <section className="space-y-3" aria-labelledby="outlook-title" data-testid="market-outlook">
        <div>
          <h2 id="outlook-title" className="text-lg font-bold">
            {t('outlook.title')}
          </h2>
          <p className="text-sm text-slate">{t('outlook.note')}</p>
        </div>
        {advice.status === 'loading' && <Loading />}
        {advice.status === 'error' && <ErrorBox error={advice.error} onRetry={reload} />}
        {advice.status === 'ok' && <SignalCard advice={advice.data} secondary />}
        <WeatherLine mandi={selection.mandi} />
      </section>

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
    </div>
  )
}
