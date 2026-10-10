/**
 * Class names and status metadata for the visual primitives (components/ui/primitives.tsx). Plain values, kept
 * apart from the components so a screen can style a native element (a link, a button, an input) the same way.
 */
import type { IconName } from './Icon'

// ---------------------------------------------------------------- cards

export type CardTone = 'surface' | 'highlight' | 'quiet' | 'caution' | 'info' | 'error' | 'positive'

// Each tone sets its own border width and colour, so no two border utilities ever compete on one card.
const CARD_TONE: Record<CardTone, string> = {
  surface: 'border border-line bg-paper shadow-(--shadow-card)',
  highlight: 'border-2 border-field bg-paper shadow-(--shadow-card)',
  quiet: 'border border-line bg-cotton',
  caution: 'border border-wheat/60 bg-wheat-soft',
  info: 'border border-transparent bg-mist',
  error: 'border border-madder/30 bg-madder-soft',
  positive: 'border border-field/25 bg-field-soft',
}

/** A rounded paper card. `tone` sets the surface; the content decides the rest. */
export function cardClass(tone: CardTone = 'surface', extra = ''): string {
  return `rounded-2xl p-5 sm:p-6 ${CARD_TONE[tone]} ${extra}`
}

// ---------------------------------------------------------------- buttons

export type ButtonVariant = 'primary' | 'outline' | 'quiet'

const BUTTON: Record<ButtonVariant, string> = {
  primary: 'bg-field text-paper hover:bg-field/90 disabled:bg-slate/40 disabled:text-paper',
  outline: 'border-2 border-field/70 bg-paper text-field hover:bg-field-soft disabled:border-line disabled:text-slate',
  quiet: 'text-field underline-offset-4 hover:underline disabled:text-slate',
}

/** Classes for a button or a link that looks like one. Every variant is at least 48px tall (NFR-05). */
export function buttonClass(variant: ButtonVariant = 'primary', extra = ''): string {
  return `inline-flex min-h-12 items-center justify-center gap-2 rounded-xl px-5 py-2 text-base font-semibold transition-colors disabled:cursor-not-allowed ${BUTTON[variant]} ${extra}`
}

// ---------------------------------------------------------------- status badges

/** The five data states of the reference system, each with its own icon so meaning never rests on colour. */
export type StatusKind = 'fresh' | 'limited' | 'stale' | 'frozen' | 'estimate' | 'synthetic' | 'neutral'

export const STATUS: Record<StatusKind, { icon: IconName | null; className: string }> = {
  fresh: { icon: 'checkCircle', className: 'bg-field-soft text-field' },
  limited: { icon: 'alert', className: 'bg-wheat-soft text-wheat-deep' },
  stale: { icon: 'clock', className: 'bg-wheat-soft text-wheat-deep' },
  frozen: { icon: 'repeat', className: 'bg-wheat-soft text-wheat-deep' },
  estimate: { icon: 'calculator', className: 'bg-mist text-slate' },
  synthetic: { icon: 'alert', className: 'tape' },
  neutral: { icon: null, className: 'bg-mist text-slate' },
}

// ---------------------------------------------------------------- form fields

/** A text input on the surface colour with a clear focus ring; the label sits above it and never disappears. */
export const inputClass =
  'min-h-12 rounded-xl border-2 border-line bg-paper px-4 py-2 text-ink placeholder:text-slate/70 focus:border-field focus:outline-none aria-invalid:border-madder'

/** The persistent label over an input. */
export const labelClass = 'block text-sm font-semibold text-ink'
