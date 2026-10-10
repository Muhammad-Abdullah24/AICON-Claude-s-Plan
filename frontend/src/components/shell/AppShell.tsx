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

/** The KASHT logo: white lettering on a transparent background, so it always sits on the green title bar. */
function Logo() {
  const { t } = useTranslation()
  return (
    <Link to="/" className="flex min-h-[44px] shrink-0 items-center rounded-lg focus-visible:outline-paper">
      <img src="/kasht-logo.webp" alt={t('app.name')} width={480} height={141} className="h-8 w-auto sm:h-9" />
    </Link>
  )
}

/** The language switch as a two-part toggle. Pressing the other language is the same switch as before. */
function LanguageToggle({ onGreen = false }: { onGreen?: boolean }) {
  const { t, i18n } = useTranslation()
  const current = i18n.language === 'en' ? 'en' : 'ur'
  const other: Lang = current === 'ur' ? 'en' : 'ur'
  // Each locale names the *other* language in lang.switchTo, so a language's own name comes from the other file.
  const nameOf = (lang: Lang) => i18n.getFixedT(lang === 'ur' ? 'en' : 'ur')('lang.switchTo')
  return (
    <div
      className={`inline-flex rounded-xl p-1 ${onGreen ? 'bg-paper/15' : 'bg-mist'}`}
      role="group"
      aria-label={t('lang.switchLabel')}
    >
      {(['ur', 'en'] as const).map((lang) => (
        <button
          key={lang}
          type="button"
          lang={lang}
          aria-pressed={lang === current}
          aria-label={lang === other ? t('lang.switchLabel') : nameOf(lang)}
          onClick={() => lang === other && void i18n.changeLanguage(other)}
          className={`min-h-[44px] min-w-[44px] rounded-lg px-2 text-sm font-semibold sm:px-3 ${
            onGreen
              ? `focus-visible:outline-paper ${lang === current ? 'bg-paper text-field shadow-sm' : 'text-paper/85 hover:text-paper'}`
              : lang === current
                ? 'bg-paper text-ink shadow-sm'
                : 'text-slate hover:text-ink'
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
    <aside className="sticky top-0 hidden h-dvh flex-col gap-6 overflow-y-auto border-e border-line bg-paper pb-6 lg:flex">
      <div className="flex min-h-16 items-center bg-field px-6">
        <Logo />
      </div>
      <nav aria-label={t('app.name')} className="flex flex-col gap-1 px-4">
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
      <div className="mx-4 mt-auto border-t border-line px-2 pt-4">
        <LanguageToggle />
      </div>
    </aside>
  )
}

function TopBar() {
  const { t, i18n } = useTranslation()
  const { meta, farmer } = useAppState()
  return (
    <header className="sticky top-0 z-20 bg-field text-paper shadow-sm">
      {/* The bar keeps one arrangement in both languages (logo left; language and profile right); only the
          words inside it change, and they keep their own reading direction. */}
      <div dir="ltr" className="flex min-h-16 items-center justify-between gap-2 px-3 sm:px-4 lg:px-8">
        <div className="lg:hidden">
          <Logo />
        </div>
        <p dir={i18n.dir()} className="hidden text-sm text-paper/90 lg:block">
          {t('data.asOf', { date: formatDate(meta.prices_as_of, i18n.language as Lang) })}
        </p>
        <div className="flex items-center gap-2">
          <div className="lg:hidden">
            <LanguageToggle onGreen />
          </div>
          <NavLink
            to="/profile"
            aria-label={farmer ? farmer.name : t('nav.profile')}
            className={({ isActive }) =>
              `flex size-[44px] shrink-0 items-center justify-center rounded-full focus-visible:outline-paper ${
                isActive ? 'bg-paper text-field' : 'bg-paper/15 text-paper hover:bg-paper/25'
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
  const { t, i18n } = useTranslation()
  const { farmer } = useAppState()
  const { pathname } = useLocation()
  const primary = NAV.slice(0, BOTTOM_COUNT)
  // "More" is its own page; it stays marked while one of the screens it lists is open.
  const moreActive = pathname === MORE_PATH || MORE_ITEMS.some((i) => i.to === pathname)

  // On the green bar: the open screen is a white pill with green text (7.6:1); the others are white at 85% (5.1:1).
  const tab = (active: boolean) =>
    `flex min-h-14 min-w-0 flex-1 flex-col items-center justify-center gap-0.5 rounded-xl px-0.5 text-center text-sm leading-tight focus-visible:outline-paper ${
      active ? 'bg-paper font-semibold text-field' : 'text-paper/85 hover:text-paper'
    }`

  return (
    <nav
      aria-label={t('app.name')}
      className="fixed inset-x-0 bottom-0 z-30 bg-field-bar px-2 pt-1.5 pb-[max(0.375rem,env(safe-area-inset-bottom))] shadow-[0_-2px_8px_rgb(25_51_61/0.12)] lg:hidden"
    >
      {/* Same tab order in both languages; only the labels change (each in its own reading direction). */}
      <ul dir="ltr" className="flex gap-0.5">
        {primary.map((item) => (
          <li key={item.to} className="flex min-w-0 flex-1">
            <NavLink to={item.to} end className={({ isActive }) => tab(isActive)}>
              <Icon name={item.icon} />
              <span dir={i18n.dir()} className="max-w-full break-words">
                {navLabel(t, item.key, farmer?.name)}
              </span>
            </NavLink>
          </li>
        ))}
        <li className="flex min-w-0 flex-1">
          <Link to={MORE_PATH} aria-current={moreActive ? 'page' : undefined} className={tab(moreActive)}>
            <Icon name="more" />
            <span dir={i18n.dir()}>{t('nav.more')}</span>
          </Link>
        </li>
      </ul>
    </nav>
  )
}
