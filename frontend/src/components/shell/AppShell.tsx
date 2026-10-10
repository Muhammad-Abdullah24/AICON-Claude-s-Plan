import { Info, User } from 'lucide-react'
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, NavLink } from 'react-router'

import { useAppState } from '../../appState'
import type { Lang } from '../../i18n'
import { formatDate } from '../../lib/format'
import { replayDate } from '../../lib/replay'
import { ReplayBanner } from '../ReplayBanner'
import { Brand } from './Brand'
import { LanguageToggle } from './LanguageToggle'
import { MORE, NAV } from './nav'

/** The date the data on screen comes from: the replay day, or AMIS's latest snapshot. Never a fixed text. */
function DataContext() {
  const { t, i18n } = useTranslation()
  const { meta } = useAppState()
  const lang = i18n.language as Lang
  return (
    <span className="text-sm text-slate" data-testid="data-context">
      {replayDate
        ? t('shell.replayContext', { date: formatDate(replayDate, lang) })
        : t('shell.dataContext', { date: formatDate(meta.prices_as_of, lang) })}
    </span>
  )
}

function ProfileButton() {
  const { t } = useTranslation()
  const { farmer } = useAppState()
  return (
    <Link
      to="/profile"
      aria-label={farmer ? farmer.name : t('nav.profile')}
      className="flex size-11 items-center justify-center rounded-full bg-slate-soft text-ink hover:bg-line"
    >
      <User aria-hidden className="size-5" />
    </Link>
  )
}

function SyntheticTape() {
  const { t } = useTranslation()
  const { meta } = useAppState()
  if (!meta.is_synthetic) return null
  return (
    <p className="tape px-4 py-1 text-center text-sm font-semibold" role="status">
      {t('data.synthetic')} · <span className="font-normal">{t('data.syntheticNote')}</span>
    </p>
  )
}

/** Desktop (≥ 1024 px): a fixed 248 px sidebar with the brand, navigation, language, profile and a note. */
function Sidebar() {
  const { t } = useTranslation()
  const { farmer, selection, cropName, mandiName } = useAppState()
  return (
    <aside
      className="sticky top-0 hidden h-dvh w-[248px] shrink-0 flex-col gap-6 overflow-y-auto border-e border-line bg-cotton px-5 py-6 lg:flex"
      aria-label={t('app.name')}
    >
      <div className="space-y-2">
        <Brand size="lg" />
        <p className="text-sm text-slate">{t('shell.productLine')}</p>
      </div>
      <nav className="flex flex-col gap-1" aria-label={t('shell.navLabel')}>
        {NAV.map(({ to, key, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end
            className={({ isActive }) =>
              `flex min-h-12 items-center gap-3 rounded-[var(--radius-control)] px-3 py-2 ${
                isActive ? 'bg-field-soft font-semibold text-field' : 'text-ink hover:bg-slate-soft'
              }`
            }
          >
            <Icon aria-hidden className="size-5 shrink-0" />
            {t(`nav.${key}`)}
          </NavLink>
        ))}
        <p className="mt-3 px-3 text-xs font-semibold text-slate">{t('nav.more')}</p>
        {MORE.map(({ to, key }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `rounded-[var(--radius-control)] px-3 py-1.5 text-sm ${isActive ? 'font-semibold text-field' : 'text-slate hover:text-ink'}`
            }
          >
            {t(`nav.${key}`)}
          </NavLink>
        ))}
      </nav>
      <LanguageToggle />
      <div className="space-y-1 border-t border-line pt-4">
        <p className="font-semibold">{farmer ? farmer.name : t('shell.guest')}</p>
        <p className="text-sm text-slate">
          {mandiName(selection.mandi)} · {cropName(selection.crop)}
        </p>
      </div>
      <p className="flex items-start gap-2 rounded-[var(--radius-control)] bg-slate-soft p-3 text-xs text-slate">
        <Info aria-hidden className="mt-0.5 size-4 shrink-0" />
        {t('shell.note')}
      </p>
    </aside>
  )
}

/** Mobile (< 1024 px): four big destinations at the bottom, labels under the icons. */
function BottomNav() {
  const { t } = useTranslation()
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-4 gap-1 border-t border-line bg-paper px-2 pt-1.5 pb-[max(0.375rem,env(safe-area-inset-bottom))] lg:hidden"
      aria-label={t('shell.navLabel')}
    >
      {NAV.filter((n) => n.primary).map(({ to, key, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end
          className={({ isActive }) =>
            `flex min-h-14 flex-col items-center justify-center gap-0.5 rounded-[var(--radius-control)] text-xs ${
              isActive ? 'bg-field-soft font-semibold text-field' : 'text-slate'
            }`
          }
        >
          <Icon aria-hidden className="size-5" />
          {t(`navShort.${key}`)}
        </NavLink>
      ))}
    </nav>
  )
}

/**
 * The responsive frame every screen sits in. Phone: a compact header and the bottom bar. Desktop: the sidebar,
 * a top bar with the data date, and a wider content area.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <SyntheticTape />
        <header className="border-b border-line bg-paper/80 lg:bg-paper">
          {/* Phone: brand at the start, language and profile at the end. */}
          <div className="flex items-center justify-between gap-3 px-5 py-3 lg:hidden">
            <Brand />
            <div className="flex items-center gap-2">
              <LanguageToggle />
              <ProfileButton />
            </div>
          </div>
          {/* Desktop: the product line at the start, the data date and profile at the end. */}
          <div className="hidden items-center justify-between gap-4 px-8 py-4 lg:flex">
            <p className="font-semibold">{t('shell.descriptor')}</p>
            <div className="flex items-center gap-3">
              <DataContext />
              <ProfileButton />
            </div>
          </div>
        </header>
        <ReplayBanner />
        <main className="mx-auto w-full max-w-6xl flex-1 px-5 pt-6 pb-28 lg:px-8 lg:pb-12">
          <div className="mb-4 lg:hidden">
            <DataContext />
          </div>
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  )
}
