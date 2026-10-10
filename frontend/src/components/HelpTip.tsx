import { useId, useState } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * A small "?" beside a word a farmer may not know (arhti money, godown, net price...). Tapping it opens one plain
 * sentence right below, in the page flow, so it never covers anything or runs off a narrow phone. Tap again to close.
 */
export function HelpTip({ text }: { text: string }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const id = useId()
  return (
    <>
      <button
        type="button"
        onClick={(e) => {
          e.preventDefault() // inside a <label>, a tap must not also focus the input
          setOpen((o) => !o)
        }}
        aria-expanded={open}
        aria-controls={id}
        aria-label={t('help.what')}
        className="ms-2 inline-flex size-12 shrink-0 items-center justify-center rounded-full align-middle"
      >
        <span
          aria-hidden
          className={`flex size-7 items-center justify-center rounded-full border-2 text-base font-bold ${
            open ? 'border-field bg-field text-paper' : 'border-field text-field'
          }`}
        >
          ?
        </span>
      </button>
      {open && (
        <span id={id} role="note" className="mt-1 block rounded-xl bg-field-soft px-3 py-2 text-base font-normal text-ink">
          {text}
        </span>
      )}
    </>
  )
}
