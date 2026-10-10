import { Check } from 'lucide-react'
import { useId } from 'react'

interface Option {
  value: string
  label: string
}

/**
 * A row of large tappable choices (crop, mandi). Easier than a dropdown on a phone in the field. Built on radio
 * inputs, so keyboard and screen readers work natively. The selected chip has a border and a check mark, not
 * just a colour.
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
      <legend className="mb-2 text-base font-semibold">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <label
            key={o.value}
            className="inline-flex min-h-11 cursor-pointer items-center gap-1.5 rounded-[var(--radius-control)] border border-line bg-paper px-4 py-1.5 text-base transition-colors hover:border-slate has-checked:border-2 has-checked:border-field has-checked:bg-field-soft has-checked:font-semibold has-checked:text-field has-focus-visible:outline-3 has-focus-visible:outline-wheat"
          >
            <input
              type="radio"
              name={name}
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
              className="peer sr-only"
            />
            <Check aria-hidden className="hidden size-4 peer-checked:block" strokeWidth={2.5} />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}
