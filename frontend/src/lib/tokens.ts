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
