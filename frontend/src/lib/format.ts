/**
 * Number and date formatting. Western digits in both languages: they are what
 * farmers see on receipts and phones (PLAN.md section 13).
 */
import type { Lang } from '../i18n'

const rupees = new Intl.NumberFormat('en-PK', { maximumFractionDigits: 0 })

/**
 * "Rs 4,250". Negative values keep their sign: "Rs -1,200". Wrapped in invisible left-to-right isolation
 * marks (U+2066 ... U+2069) so a figure inside an Urdu sentence is never reordered by right-to-left layout, and
 * with a non-breaking space so "Rs" never wraps away from its number.
 */
export function formatRs(value: number): string {
  return `\u2066Rs\u00a0${rupees.format(Math.round(value))}\u2069`
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

/**
 * Reads a number typed by a farmer. Urdu keyboards type Urdu digits (۱۰۰) or
 * Arabic-Indic digits (١٠٠), so those become Western digits first; thousands
 * separators and spaces are ignored. Returns null when it is not a number.
 */
export function parseTypedNumber(text: string): number | null {
  const western = text
    .replace(/[۰-۹]/g, (d) => String(d.charCodeAt(0) - 0x06f0))
    .replace(/[٠-٩]/g, (d) => String(d.charCodeAt(0) - 0x0660))
    .replace(/٫/g, '.') // Arabic decimal separator
    .replace(/[,٬\s]/g, '') // thousands separators and spaces
  if (!/^\d+(\.\d+)?$/.test(western)) return null
  return Number(western)
}

/** ISO date `weeks` weeks after `iso`. */
export function addWeeks(iso: string, weeks: number): string {
  const d = parseDate(iso)
  d.setDate(d.getDate() + weeks * 7)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}
