import type { ReactNode } from 'react'

/**
 * A number with a persistent label (never only a placeholder), its unit inside the field, an optional helper
 * line and an inline error. `prefix` puts "Rs" before the figure for rupee amounts. Digits keep their LTR order.
 */
export function NumberField({
  id,
  label,
  value,
  onChange,
  unit,
  prefix,
  helper,
  error,
  placeholder,
}: {
  id: string
  label: string
  value: string
  onChange: (text: string) => void
  unit?: string
  prefix?: string
  helper?: ReactNode
  error?: string | null
  placeholder?: string
}) {
  const describedBy = [error ? `${id}-error` : null, helper ? `${id}-help` : null].filter(Boolean).join(' ')
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="block text-base font-semibold">
        {label}
      </label>
      <div
        className={`flex min-h-14 items-center gap-3 rounded-[var(--radius-control)] border bg-paper px-4 focus-within:border-ink ${
          error ? 'border-madder' : 'border-line'
        }`}
      >
        {unit && <span className="text-sm text-slate">{unit}</span>}
        <div className="flex flex-1 items-baseline justify-end gap-2" dir="ltr">
          {prefix && <span className="figures text-lg font-normal text-slate">{prefix}</span>}
          <input
            id={id}
            inputMode="decimal"
            autoComplete="off"
            value={value}
            placeholder={placeholder}
            onChange={(e) => onChange(e.target.value)}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy || undefined}
            className="figures w-full min-w-0 bg-transparent text-2xl outline-none placeholder:text-slate/50"
          />
        </div>
      </div>
      {helper && !error && (
        <p id={`${id}-help`} className="text-xs text-slate">
          {helper}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-sm text-madder" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
