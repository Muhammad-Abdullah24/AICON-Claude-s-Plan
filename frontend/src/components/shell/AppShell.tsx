import { type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, NavLink, useLocation } from 'react-router'

import { useAppState } from '../../appState'
import type { Lang } from '../../i18n'
import { formatDate } from '../../lib/format'
import { ReplayBanner } from '../ReplayBanner'
import { Icon } from '../ui/Icon'
import { BOTTOM_COUNT, MORE_ITEMS, MORE_PATH, NAV } from './nav'

/**
 * The responsive frame: on a desktop a fixed sidebar (left) and a slim top bar; on a phone a compact header and
 * a bottom navigation bar. Routes, links and the language switch behave exactly as before.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const { meta } = useAppState()
  return (
    <div className="app-shell min-h-dvh lg:grid lg:grid-cols-[15rem_minmax(0,1fr)]">
      <Sidebar />
      <div className="flex min-h-dvh min-w-0 flex-col">
        {meta.is_synthetic && (
          <p className="tape px-4 py-1 text-center text-sm font-semibold" role="status">
            {t('data.synthetic')} · <span className="font-normal">{t('data.syntheticNote')}</span>
          </p>
        )}
        <TopBar />
        <ReplayBanner />
        <div className="flex-1 pb-28 lg:pb-10">{children}</div>
      </div>
      <BottomNav />
    </div>
  )
}

function Brand({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation()
  return (
    <Link to="/" className="flex items-center gap-2.5 rounded-xl text-ink">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-field-soft text-field sm:size-10">
        <Icon name="wheat" className="size-6" />
      </span>
      <span className="leading-tight">
        <span className="block text-xl font-bold whitespace-nowrap">{t('app.name')}</span>
        {!compact && <span className="block text-sm text-slate">{t('app.tagline')}</span>}
      </span>
    </Link>
  )
}

/** The language switch as a two-part toggle. Pressing the other language is the same switch as before. */
function LanguageToggle() {
  const { t, i18n } = useTranslation()
  const current = i18n.language === 'en' ? 'en' : 'ur'
  const other: Lang = current === 'ur' ? 'en' : 'ur'
  // Each locale names the *other* language in lang.switchTo, so a language's own name comes from the other file.
  const nameOf = (lang: Lang) => i18n.getFixedT(lang === 'ur' ? 'en' : 'ur')('lang.switchTo')
  return (
    <div className="inline-flex rounded-xl bg-mist p-1" role="group" aria-label={t('lang.switchLabel')}>
      {(['ur', 'en'] as const).map((lang) => (
        <button
          key={lang}
          type="button"
          lang={lang}
          aria-pressed={lang === current}
          aria-label={lang === other ? t('lang.switchLabel') : nameOf(lang)}
          onClick={() => lang === other && void i18n.changeLanguage(other)}
          className={`min-h-[44px] min-w-[44px] rounded-lg px-2 text-sm font-semibold sm:px-3 ${
            lang === current ? 'bg-paper text-ink shadow-sm' : 'text-slate hover:text-ink'
          }`}
        >
          {lang === 'en' ? (
            <>
              {/* A narrow phone shows the language code, as in the reference; the full name from 640px. */}
              <span className="sm:hidden">EN</span>
              <span className="hidden sm:inline">{nameOf(lang)}</span>
            </>
          ) : (
            nameOf(lang)
          )}
        </button>
      ))}
    </div>
  )
}

function navLabel(t: (k: string) => string, key: string, farmerName?: string) {
  return key === 'profile' && farmerName ? farmerName : t(`nav.${key}`)
}

function Sidebar() {
  const { t } = useTranslation()
  const { farmer } = useAppState()
  return (
    <aside className="sticky top-0 hidden h-dvh flex-col gap-6 overflow-y-auto border-e border-line bg-paper px-4 py-6 lg:flex">
      <div className="px-2">
        <Brand />
      </div>
      <nav aria-label={t('app.name')} className="flex flex-col gap-1">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end
            className={({ isActive }) =>
              `flex min-h-12 items-center gap-3 rounded-xl px-3 py-2 text-base ${
                isActive ? 'bg-field-soft font-semibold text-field' : 'text-ink hover:bg-cotton'
              }`
            }
          >
            <Icon name={item.icon} />
            <span>{navLabel(t, item.key, farmer?.name)}</span>
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto border-t border-line px-2 pt-4">
        <LanguageToggle />
      </div>
    </aside>
  )
}

function TopBar() {
  const { t, i18n } = useTranslation()
  const { meta, farmer } = useAppState()
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-paper/95 backdrop-blur">
      <div className="flex min-h-16 items-center justify-between gap-2 px-3 sm:px-4 lg:px-8">
        <div className="lg:hidden">
          <Brand compact />
        </div>
        <p className="hidden text-sm text-slate lg:block">
          {t('data.asOf', { date: formatDate(meta.prices_as_of, i18n.language as Lang) })}
        </p>
        <div className="flex items-center gap-2">
          <div className="lg:hidden">
            <LanguageToggle />
          </div>
          <NavLink
            to="/profile"
            aria-label={farmer ? farmer.name : t('nav.profile')}
            className={({ isActive }) =>
              `flex size-[44px] shrink-0 items-center justify-center rounded-full ${
                isActive ? 'bg-field-soft text-field' : 'bg-cotton text-ink hover:bg-mist'
              }`
            }
          >
            <Icon name="user" />
          </NavLink>
        </div>
      </div>
    </header>
  )
}

function BottomNav() {
  const { t } = useTranslation()
  const { farmer } = useAppState()
  const { pathname } = useLocation()
  const primary = NAV.slice(0, BOTTOM_COUNT)
  // "More" is its own page; it stays marked while one of the screens it lists is open.
  const moreActive = pathname === MORE_PATH || MORE_ITEMS.some((i) => i.to === pathname)

  const tab = (active: boolean) =>
    `flex min-h-14 min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-xl px-0.5 text-center text-sm leading-tight ${
      active ? 'bg-field-soft font-semibold text-field' : 'text-slate hover:text-ink'
    }`

  return (
    <nav
      aria-label={t('app.name')}
      className="fixed inset-x-0 bottom-0 z-30 border-t border-line bg-paper/95 px-2 pt-1.5 pb-[max(0.375rem,env(safe-area-inset-bottom))] backdrop-blur lg:hidden"
    >
      <ul className="flex gap-0.5">
        {primary.map((item) => (
          <li key={item.to} className="flex min-w-0 flex-1">
            <NavLink to={item.to} end className={({ isActive }) => tab(isActive)}>
              <Icon name={item.icon} />
              <span className="max-w-full break-words">{navLabel(t, item.key, farmer?.name)}</span>
            </NavLink>
          </li>
        ))}
        <li className="flex min-w-0 flex-1">
          <Link to={MORE_PATH} aria-current={moreActive ? 'page' : undefined} className={tab(moreActive)}>
            <Icon name="more" />
            <span>{t('nav.more')}</span>
          </Link>
        </li>
      </ul>
    </nav>
  )
}
