import { Wheat } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

/** The wordmark: the Urdu name, "FARMSIGHT" under it, and a grain motif. */
export function Brand({ size = 'md' }: { size?: 'md' | 'lg' }) {
  const { t } = useTranslation()
  return (
    <Link to="/" className="inline-flex items-center gap-2" aria-label={t('app.name')}>
      <span className="flex flex-col leading-none">
        <span lang="ur" className={`font-urdu font-bold ${size === 'lg' ? 'text-2xl' : 'text-xl'}`}>
          فارم سائٹ
        </span>
        <span lang="en" className="font-[family-name:var(--font-latin)] text-[0.6rem] font-bold tracking-wider text-field">
          FARMSIGHT
        </span>
      </span>
      <Wheat aria-hidden className={`${size === 'lg' ? 'size-8' : 'size-7'} text-field`} strokeWidth={1.75} />
    </Link>
  )
}
