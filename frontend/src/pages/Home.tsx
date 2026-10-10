import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { useAppState } from '../appState'
import { NewsBanner } from '../components/NewsBanner'
import { SelectionBar } from '../components/SelectionBar'
import { Icon, type IconName } from '../components/ui/Icon'
import { buttonClass } from '../components/ui/styles'
import { WaitPlan } from '../components/WaitPlan'
import { WeatherLine } from '../components/WeatherLine'

/** The pivot's question first (docs/PIVOT.md F1): can you afford to wait, and with whose money? */
export function Home() {
  const { t } = useTranslation()
  const { selection } = useAppState()

  const actions: { to: string; label: string; icon: IconName }[] = [
    { to: '/why', label: t('actions.why'), icon: 'why' },
    { to: '/compare', label: t('actions.compare'), icon: 'pin' },
    { to: '/grow', label: t('actions.grow'), icon: 'sprout' },
    { to: '/chat', label: t('actions.ask'), icon: 'chat' },
  ]

  // One column on a phone, in reading order. On a desktop the news sits beside the plan; the items are placed on
  // the grid rather than reordered, so the reading and keyboard order stay the same as on a phone.
  return (
    <div className="flex flex-col gap-5 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,20rem)] lg:grid-rows-[auto_auto_auto_1fr] lg:items-start lg:gap-x-6">
      <div className="lg:col-start-1 lg:row-start-1">
        <SelectionBar withQuantity />
      </div>
      <div className="empty:hidden lg:sticky lg:top-24 lg:col-start-2 lg:row-span-4 lg:row-start-1">
        <NewsBanner crop={selection.crop} mandi={selection.mandi} />
      </div>
      <div className="lg:col-start-1 lg:row-start-2">
        <WaitPlan />
      </div>
      <div className="empty:hidden lg:col-start-1 lg:row-start-3">
        <WeatherLine mandi={selection.mandi} />
      </div>
      <nav className="grid grid-cols-2 gap-3 lg:col-start-1 lg:row-start-4" aria-label={t('app.name')}>
        {actions.map((a) => (
          <Link key={a.to} to={a.to} className={buttonClass('outline', 'min-h-14 text-center')}>
            <Icon name={a.icon} />
            <span>{a.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  )
}
