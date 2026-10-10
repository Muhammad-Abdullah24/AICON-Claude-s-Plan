import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink, useLocation } from 'react-router'

import { useAppState } from '../appState'

export function Header() {
  const { t, i18n } = useTranslation()
  const { meta, farmer } = useAppState()
  const other = i18n.language === 'ur' ? 'en' : 'ur'
  const nav = useRef<HTMLElement>(null)
  const { pathname } = useLocation()
  // True while tabs are hidden past the row's end edge (right in English, left in Urdu): the edge then fades,
  // so a farmer can see the row scrolls. scrollLeft runs negative in right-to-left layout, hence Math.abs.
  const [moreAtEnd, setMoreAtEnd] = useState(false)
  const measure = useCallback(() => {
    const el = nav.current
    if (!el) return
    // The row's own end padding is not a hidden tab: without this, the fade stayed on at the very end.
    const pad = parseFloat(getComputedStyle(el).paddingInlineEnd) || 0
    setMoreAtEnd(el.scrollWidth - el.clientWidth - Math.abs(el.scrollLeft) - pad > 2)
  }, [])

  useEffect(() => {
    const el = nav.current
    if (!el) return
    // The open screen's tab is always in view (e.g. Profile, the last one), centred so it never sits under the fade.
    el.querySelector<HTMLElement>('[aria-current="page"]')?.scrollIntoView({ block: 'nearest', inline: 'center' })
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [pathname, i18n.language, measure])

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
          className="inline-flex min-h-12 items-center rounded-full border border-cotton/40 px-5 text-sm hover:bg-cotton/10"
        >
          {t('lang.switchTo')}
        </button>
      </div>
      {/* Eight screens. On a phone the row scrolls sideways, with a fade at the end edge while tabs are hidden.
          From 640px the row gets the width to show every tab, and wraps rather than hide one if it still can't. */}
      <nav
        ref={nav}
        onScroll={measure}
        className={`mx-auto flex max-w-xl gap-1 overflow-x-auto px-4 pt-2 whitespace-nowrap [scrollbar-width:none] sm:max-w-3xl sm:flex-wrap sm:overflow-visible ${
          moreAtEnd ? 'mask-r-from-80% rtl:mask-r-from-100% rtl:mask-l-from-80%' : ''
        }`}
        aria-label={t('app.name')}
      >
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
              `flex min-h-12 shrink-0 items-center rounded-t-lg px-3 py-2 text-base ${
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
