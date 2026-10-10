import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { useAppState } from '../appState'
import { MORE_ITEMS } from '../components/shell/nav'
import { Icon } from '../components/ui/Icon'

/** The phone's "More" page: the screens that are not in the bottom bar. Tapping one opens that screen. */
export function More() {
  const { t } = useTranslation()
  const { farmer } = useAppState()
  return (
    <div className="space-y-5">
      <h2 className="text-2xl font-bold">{t('nav.more')}</h2>
      <ul className="space-y-3">
        {MORE_ITEMS.map((item) => (
          <li key={item.to}>
            <Link
              to={item.to}
              className="flex min-h-16 items-center gap-4 rounded-2xl border border-line bg-paper px-5 py-3 text-lg font-semibold text-ink shadow-(--shadow-card) hover:border-field/40 hover:bg-field-soft"
            >
              <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-field-soft text-field">
                <Icon name={item.icon} className="size-6" />
              </span>
              <span className="flex-1">{item.key === 'profile' && farmer ? farmer.name : t(`nav.${item.key}`)}</span>
              {/* Points forward: right in English, left in Urdu. */}
              <Icon name="chevron" className="size-5 -rotate-90 text-slate rtl:rotate-90" />
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
