/**
 * Reads colour tokens from index.css at runtime, so charts (which need plain
 * colour strings, not CSS variables) stay in step with the design system.
 */
const NAMES = ['ink', 'wheat', 'wheat-soft', 'wheat-deep', 'madder', 'field', 'slate', 'line'] as const
export type TokenName = (typeof NAMES)[number]

export function readTokens(): Record<TokenName, string> {
  const style = getComputedStyle(document.documentElement)
  return Object.fromEntries(
    NAMES.map((n) => [n, style.getPropertyValue(`--color-${n}`).trim()]),
  ) as Record<TokenName, string>
}

/** Chart axis labels: the blueprint's 18px minimum (NFR-05) applies to charts too. */
export const CHART_TICK_PX = 18
/** Room for a "12,345" label at CHART_TICK_PX in the monospace figure font. */
export const CHART_Y_AXIS_WIDTH = 72
/** Minimum gap between date labels, so 18px labels never collide on a 360px phone. */
export const CHART_MIN_TICK_GAP = 64
