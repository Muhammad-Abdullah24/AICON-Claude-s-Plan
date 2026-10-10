import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router'

type Variant = 'primary' | 'secondary' | 'text'

const BASE =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-control)] px-5 py-2.5 text-base font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50'
const VARIANT: Record<Variant, string> = {
  primary: 'bg-field text-paper hover:bg-field/90',
  secondary: 'border border-field bg-paper text-field hover:bg-field-soft',
  text: 'text-field hover:underline',
}

function buttonClass(variant: Variant = 'primary', wide = false): string {
  return `${BASE} ${VARIANT[variant]} ${wide ? 'w-full' : ''}`
}

/** Field green is kept for the one next step on a screen; every target is at least 44 px tall. */
export function Button({
  variant = 'primary',
  wide = false,
  className = '',
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; wide?: boolean }) {
  return <button type="button" className={`${buttonClass(variant, wide)} ${className}`} {...rest} />
}

export function ButtonLink({
  to,
  variant = 'primary',
  wide = false,
  children,
}: {
  to: string
  variant?: Variant
  wide?: boolean
  children: ReactNode
}) {
  return (
    <Link to={to} className={buttonClass(variant, wide)}>
      {children}
    </Link>
  )
}
