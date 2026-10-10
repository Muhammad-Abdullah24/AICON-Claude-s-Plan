/**
 * How an offer-check result is shown. Pure display decisions only: every number and every judgement
 * (status, reference strength, alternatives "better after transport") comes from the API, which gets them from
 * the engine. Nothing here calculates a price.
 */
import type { OfferCheckResponse } from '../api/client'

export type OfferResult = OfferCheckResponse
export type OfferAlternative = OfferCheckResponse['alternative_mandis'][number]
export type Tone = 'below' | 'within' | 'above' | 'limited'

const TONE: Record<OfferResult['result_status'], Tone> = {
  BELOW_REFERENCE_RANGE: 'below',
  WITHIN_REFERENCE_RANGE: 'within',
  ABOVE_REFERENCE_RANGE: 'above',
  REFERENCE_DATA_LIMITED: 'limited',
}

/** The headline: below / within / above the recent reference range, or "reference data is limited". */
export function tone(r: OfferResult): Tone {
  return TONE[r.result_status]
}

/** Which way the offer sits from the latest reported price. */
export function side(perMaund: number): 'below' | 'above' | 'equal' {
  return perMaund < 0 ? 'below' : perMaund > 0 ? 'above' : 'equal'
}

/** Why the reference is weak (explained in a sentence of its own, not in the assumptions list). */
export const STRENGTH_LIMITS = new Set(['STALE_REFERENCE', 'FROZEN_REFERENCE', 'FEW_REFERENCE_DAYS', 'SAME_PRICE_ALL_WINDOW'])

/** The standing assumptions to list under the result. Synthetic data and commission have their own lines. */
export function assumptions(r: OfferResult): string[] {
  return r.limitations.filter(
    (c) => !STRENGTH_LIMITS.has(c) && c !== 'SYNTHETIC_DATA' && c !== 'COMMISSION_FARMER_ESTIMATE',
  )
}

/** The non-prescriptive next steps are shown whenever the offer is below the reported prices. */
export function showNextSteps(r: OfferResult): boolean {
  return r.range_position === 'BELOW_REFERENCE_RANGE'
}

/** An alternative mandi in one word, from the API's own flags. */
export function alternativeVerdict(a: OfferAlternative): 'noData' | 'unknown' | 'better' | 'higherNotBetter' | 'notBetter' {
  if (!a.has_data) return 'noData'
  if (a.better_after_transport == null) return 'unknown'
  if (a.better_after_transport) return 'better'
  return a.higher_quote_not_better ? 'higherNotBetter' : 'notBetter'
}

/** Words the offer check must never show: the reference is not a fair, true or guaranteed price. */
// "guaranteed" is allowed only when negated ("not a guaranteed future price"), never as a claim.
export const FORBIDDEN_WORDS = [
  /fair (price|range)/i,
  /true price/i,
  /(?<!\bnot (a )?)guaranteed/i,
  /\bscam\b/i,
  /unfair/i,
  /exploit/i,
]
