/**
 * Number and date formatting. Western digits in both languages: they are what
 * farmers see on receipts and phones (PLAN.md section 13).
 */
import type { Lang } from '../i18n'

const rupees = new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 })

/** "Rs 4,250". Negative values keep their sign: "Rs -1,200". */
export function formatRs(value: number): string {
  return `Rs ${rupees.format(Math.round(value))}`
}

export function formatNumber(value: number): string {
  return rupees.format(value)
}

function locale(lang: Lang): string {
  return lang === 'ur' ? 'ur-PK-u-nu-latn' : 'en-GB'
}

/** Parses "2026-10-04" as a calendar date, not a UTC instant, so it never shifts a day. */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function formatDate(iso: string, lang: Lang): string {
  return new Intl.DateTimeFormat(locale(lang), { day: 'numeric', month: 'long', year: 'numeric' }).format(
    parseDate(iso),
  )
}

export function formatMonth(iso: string, lang: Lang): string {
  return new Intl.DateTimeFormat(locale(lang), { month: 'short', year: '2-digit' }).format(parseDate(iso))
}

/** ISO date `weeks` weeks after `iso`. */
export function addWeeks(iso: string, weeks: number): string {
  const d = parseDate(iso)
  d.setDate(d.getDate() + weeks * 7)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}
