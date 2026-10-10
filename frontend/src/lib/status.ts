/**
 * Which status badge a reference gets. Mapped only from real API fields (reference_strength, is_stale,
 * price_unchanged_since, is_synthetic): the badge never says more than the data does.
 */
export type BadgeKind =
  | 'fresh'
  | 'limited'
  | 'stale'
  | 'frozen'
  | 'samePrice'
  | 'fewDays'
  | 'estimate'
  | 'illustrative'
  | 'error'

export type Strength = 'STRONG' | 'LIMITED_STALE' | 'LIMITED_FROZEN' | 'LIMITED_FEW_DAYS' | 'LIMITED_SAME_PRICE'

const BY_STRENGTH: Record<Strength, BadgeKind> = {
  STRONG: 'fresh',
  LIMITED_STALE: 'stale',
  LIMITED_FROZEN: 'frozen',
  LIMITED_FEW_DAYS: 'fewDays',
  LIMITED_SAME_PRICE: 'samePrice',
}

/** A reference's badge. Without a strength (older rows), fall back to the stale and frozen flags alone. */
export function referenceBadge(r: {
  reference_strength?: Strength | null
  is_stale?: boolean | null
  price_unchanged_since?: string | null
}): BadgeKind {
  if (r.reference_strength) return BY_STRENGTH[r.reference_strength]
  if (r.is_stale) return 'stale'
  if (r.price_unchanged_since) return 'frozen'
  return 'fresh'
}

/** True when a reference may be leaned on; anything else is shown as limited, never as a strong result. */
export function isStrong(r: { reference_strength?: Strength | null }): boolean {
  return r.reference_strength === 'STRONG'
}
