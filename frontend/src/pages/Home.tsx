import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { useAppState } from '../appState'
import { NewsBanner } from '../components/NewsBanner'
import { SelectionBar } from '../components/SelectionBar'
import { WaitPlan } from '../components/WaitPlan'
import { WeatherLine } from '../components/WeatherLine'

/** The pivot's question first (docs/PIVOT.md F1): can you afford to wait, and with whose money? */
export function Home() {
  const { t } = useTranslation()
  const { selection } = useAppState()

  const actions = [
    { to: '/why', label: t('actions.why') },
    { to: '/compare', label: t('actions.compare') },
    { to: '/grow', label: t('actions.grow') },
    { to: '/chat', label: t('actions.ask') },
  ]

  return (
    <div className="space-y-5">
      <SelectionBar withQuantity />
      <NewsBanner crop={selection.crop} mandi={selection.mandi} />
      <WaitPlan />
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
    </div>
  )
}
