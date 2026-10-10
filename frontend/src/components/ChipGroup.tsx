import { useId } from 'react'

import { Icon } from './ui/Icon'

interface Option {
  value: string
  label: string
}

/**
 * A row of large tappable choices. Easier than a dropdown on a phone in the
 * field. Built on radio inputs, so keyboard and screen readers work natively.
 * The chosen chip is marked by its border, a tint and a check mark, not by colour alone.
 */
export function ChipGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: Option[]
  value: string
  onChange: (value: string) => void
}) {
  const name = useId()
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-semibold text-ink">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <label
            key={o.value}
            className="group/chip inline-flex min-h-12 cursor-pointer items-center gap-1.5 rounded-xl border-2 border-line bg-paper px-4 py-1.5 text-base text-ink transition-colors hover:border-field/40 has-checked:border-field has-checked:bg-field-soft has-checked:font-semibold has-checked:text-field has-focus-visible:outline-3 has-focus-visible:outline-field"
          >
            <input
              type="radio"
              name={name}
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
              className="sr-only"
            />
            <span className="hidden group-has-checked/chip:inline-flex">
              <Icon name="check" className="size-4" />
            </span>
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}
