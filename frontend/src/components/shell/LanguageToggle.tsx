import { useTranslation } from 'react-i18next'

const OPTIONS = [
  { lang: 'ur', label: 'اردو' },
  { lang: 'en', label: 'EN' },
] as const

/** Urdu / English as a two-part segmented control; the current language is the raised segment. */
export function LanguageToggle() {
  const { t, i18n } = useTranslation()
  return (
    <div role="group" aria-label={t('lang.label')} className="inline-flex rounded-[var(--radius-control)] bg-slate-soft p-1">
      {OPTIONS.map((o) => {
        const active = i18n.language === o.lang
        return (
          <button
            key={o.lang}
            type="button"
            lang={o.lang}
            aria-pressed={active}
            onClick={() => void i18n.changeLanguage(o.lang)}
            className={`min-h-11 min-w-12 rounded-[10px] px-3 text-sm ${
              active ? 'bg-paper font-semibold text-ink shadow-sm' : 'text-slate hover:text-ink'
            }`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
