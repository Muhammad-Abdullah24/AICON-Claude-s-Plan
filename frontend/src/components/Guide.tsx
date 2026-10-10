import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { OPEN_GUIDE_EVENT } from '../lib/guide'
import { Icon, type IconName } from './ui/Icon'

const SEEN_KEY = 'kasht.guide.seen.v1'

function seen(): boolean {
  try {
    return localStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return true // storage blocked (private window): never nag on every page load
  }
}

/**
 * A first-visit guide: what the app is for and where to start, in four steps a farmer can tap straight into.
 * Shown once (remembered in this browser), and again whenever the header's "?" is pressed.
 */
export function Guide() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(() => !seen())
  const startRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const show = () => setOpen(true)
    window.addEventListener(OPEN_GUIDE_EVENT, show)
    return () => window.removeEventListener(OPEN_GUIDE_EVENT, show)
  }, [])

  useEffect(() => {
    if (!open) return
    startRef.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  function close() {
    setOpen(false)
    try {
      localStorage.setItem(SEEN_KEY, '1')
    } catch {
      // storage blocked: the guide simply shows again next time
    }
  }

  if (!open) return null
  const steps: { to: string; icon: IconName; title: string; text: string }[] = [
    { to: '/', icon: 'clock', title: t('guide.s1title'), text: t('guide.s1') },
    { to: '/loan', icon: 'wallet', title: t('guide.s2title'), text: t('guide.s2') },
    { to: '/compare', icon: 'pin', title: t('guide.s3title'), text: t('guide.s3') },
  ]
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 p-3 sm:items-center" onClick={close}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-title"
        onClick={(e) => e.stopPropagation()}
        className="max-h-[92dvh] w-full max-w-md space-y-3 overflow-y-auto rounded-3xl bg-paper p-4 pb-0 shadow-xl"
      >
        <h2 id="guide-title" className="text-2xl font-bold">
          {t('guide.title')}
        </h2>
        <p className="text-base text-slate">{t('guide.intro')}</p>
        <ol className="space-y-2">
          {steps.map((s, n) => (
            <li key={s.to}>
              <Link
                to={s.to}
                onClick={close}
                className="flex min-h-14 items-start gap-3 rounded-2xl border border-line px-3 py-2 hover:bg-cotton"
              >
                <span className="figures flex size-8 shrink-0 items-center justify-center rounded-full bg-field text-paper">
                  {n + 1}
                </span>
                <span>
                  <span className="flex items-center gap-2 font-bold">
                    <Icon name={s.icon} className="size-5 text-field" />
                    {s.title}
                  </span>
                  <span className="block text-base text-slate">{s.text}</span>
                </span>
              </Link>
            </li>
          ))}
        </ol>
        <p className="flex items-center gap-2 text-base">
          <span
            aria-hidden
            className="flex size-7 items-center justify-center rounded-full border-2 border-field font-bold text-field"
          >
            ?
          </span>
          {t('guide.tip')}
        </p>
        <div className="sticky bottom-0 -mx-4 bg-paper px-4 pt-1 pb-4">
          <button
            ref={startRef}
            type="button"
            onClick={close}
            className="min-h-14 w-full rounded-2xl bg-field px-4 py-3 text-lg font-bold text-paper"
          >
            {t('guide.start')}
          </button>
        </div>
      </div>
    </div>
  )
}
