import { useId } from 'react'

interface Option {
  value: string
  label: string
}

/**
 * A row of large tappable choices. Easier than a dropdown on a phone in the
 * field. Built on radio inputs, so keyboard and screen readers work natively.
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
      <legend className="mb-1 text-sm text-slate">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <label
            key={o.value}
            className="cursor-pointer rounded-xl border-2 border-line bg-paper px-4 py-1.5 text-base transition-colors has-checked:border-ink has-checked:bg-ink has-checked:text-cotton has-focus-visible:outline-3 has-focus-visible:outline-wheat"
          >
            <input
              type="radio"
              name={name}
              value={o.value}
              checked={value === o.value}
              onChange={() => onChange(o.value)}
              className="sr-only"
            />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  )
}
