/**
 * What to Grow, made cautious (F4): which crops may be compared, and how each season and the wheat policy context
 * are worded. Pure functions, so they are tested without rendering (src/pages/growLogic.test.ts).
 *
 * The API decides everything (ml/decision/grow.py): the season groups, which crops are ranked and why the others
 * are not. This file only turns those answers into translation keys and parameters.
 */
import type { CropPlanItem, CropPlanResponse } from '../api/client'

export type SeasonSummary = CropPlanResponse['seasons'][number]
export type SupportPriceContext = CropPlanResponse['support_price_context']
export type ContextNote = CropPlanItem['notes'][number]

export interface SeasonSection extends SeasonSummary {
  items: CropPlanItem[]
}

/** Crop items grouped under their season, in the API's season order; ranked crops keep the API's order (first). */
export function seasonSections(plan: Pick<CropPlanResponse, 'items' | 'seasons'>): SeasonSection[] {
  // An older API without seasons (a deploy half-done) gives no sections instead of crashing the screen.
  return (plan.seasons ?? []).map((s) => ({ ...s, items: plan.items.filter((i) => i.season === s.season) }))
}

export interface Line {
  key: string
  params: Record<string, string | number>
}

/** Why a season is, or is not, compared. */
export function seasonStatusLine(s: SeasonSummary): Line {
  return { key: `grow.seasonStatus.${s.status}`, params: { n: s.n_crops, comparable: s.n_comparable } }
}

/** "Not ranked: the reference price is old, ..." for a crop without a rank; null for a ranked crop. */
export function notRankedKeys(item: CropPlanItem): string[] | null {
  if (item.rank != null) return null
  return item.evidence_issues.map((i) => `grow.issues.${i}`)
}

/** Isolates a value inside a sentence so a date or name keeps its own direction in Urdu (U+2068 ... U+2069). */
export function isolate(text: string): string {
  return `⁨${text}⁩`
}

/**
 * The wheat support-price context. Always paired with `grow.policy.limit` on screen: policy news is not a mandi price
 * and not a price anyone is guaranteed. `formatDate` is passed in so the date follows the screen's language.
 */
export function policyLine(ctx: SupportPriceContext, lang: 'ur' | 'en', formatDate: (iso: string) => string): Line {
  if (ctx.state === 'UNAVAILABLE' || !ctx.event) return { key: 'grow.policy.UNAVAILABLE', params: {} }
  const e = ctx.event
  return {
    key: `grow.policy.${ctx.state}`,
    params: {
      text: isolate(lang === 'ur' ? e.text_ur : e.text_en),
      source: isolate(e.source),
      date: isolate(formatDate(e.date)),
    },
  }
}

/** A context note's sentence, with its source and the crop's own season months. */
export function noteLine(
  note: ContextNote,
  item: Pick<CropPlanItem, 'sowing_months' | 'harvest_months'>,
  monthName: (m: number) => string,
  formatDate: (iso: string) => string,
): Line {
  const span = ([a, b]: readonly [number, number]) => (a === b ? monthName(a) : `${monthName(a)}–${monthName(b)}`)
  return {
    key: `grow.notes.${note.id}`,
    params: {
      sow: isolate(span(item.sowing_months)),
      harvest: isolate(span(item.harvest_months)),
      source: isolate(note.source),
      date: isolate(formatDate(note.source_date)),
    },
  }
}
