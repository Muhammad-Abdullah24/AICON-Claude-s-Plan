import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'

import { useAppState } from '../appState'

export function Header() {
  const { t, i18n } = useTranslation()
  const { meta, farmer } = useAppState()
  const other = i18n.language === 'ur' ? 'en' : 'ur'

  return (
    <header className="bg-ink text-cotton">
      {meta.is_synthetic && (
        <p className="tape px-4 py-0.5 text-center text-sm font-semibold" role="status">
          {t('data.synthetic')} · <span className="font-normal">{t('data.syntheticNote')}</span>
        </p>
      )}
      <div className="mx-auto flex max-w-xl items-center justify-between gap-3 px-4 pt-3">
        <div>
          <h1 className="text-2xl font-bold">{t('app.name')}</h1>
          <p className="text-sm text-wheat-soft">{t('app.tagline')}</p>
        </div>
        <button
          type="button"
          lang={other}
          aria-label={t('lang.switchLabel')}
          onClick={() => void i18n.changeLanguage(other)}
          className="rounded-full border border-cotton/40 px-4 py-1.5 text-sm hover:bg-cotton/10"
        >
          {t('lang.switchTo')}
        </button>
      </div>
      {/* Eight screens: the row scrolls sideways on a phone rather than wrapping. */}
      <nav className="mx-auto flex max-w-xl gap-1 overflow-x-auto px-4 pt-2 whitespace-nowrap [scrollbar-width:none]" aria-label={t('app.name')}>
        {[
          { to: '/', label: t('nav.home') },
          { to: '/why', label: t('nav.why') },
          { to: '/compare', label: t('nav.compare') },
          { to: '/grow', label: t('nav.grow') },
          { to: '/history', label: t('nav.history') },
          { to: '/margin', label: t('nav.margin') },
          { to: '/chat', label: t('nav.chat') },
          { to: '/profile', label: farmer ? farmer.name : t('nav.profile') },
        ].map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            className={({ isActive }) =>
              `shrink-0 rounded-t-lg px-3 py-2 text-base ${
                isActive ? 'bg-cotton font-bold text-ink' : 'text-cotton/80 hover:text-cotton'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </header>
  )
}
