import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'

import { api, QUESTION_MAX, type ChatResponse } from '../api/client'
import { useAppState } from '../appState'
import { SelectionBar } from '../components/SelectionBar'
import { ErrorBox } from '../components/Status'

interface Turn {
  question: string
  reply?: ChatResponse
  error?: unknown
}

/** A free question about the selected crop and mandi, answered from the farmer's own advice (UC-09). */
export function Chat() {
  const { t } = useTranslation()
  const { selection, quantity } = useAppState()
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [busy, setBusy] = useState(false)
  const tooLong = question.length > QUESTION_MAX

  function submit(e: FormEvent) {
    e.preventDefault()
    const q = question.trim()
    if (!q || tooLong || busy) return
    setBusy(true)
    setQuestion('')
    setTurns((ts) => [...ts, { question: q }])
    const done = (patch: Partial<Turn>) =>
      setTurns((ts) => ts.map((turn, i) => (i === ts.length - 1 ? { ...turn, ...patch } : turn)))
    api
      .chat({ question: q, crop: selection.crop, mandi: selection.mandi, quantity_maund: quantity })
      .then((reply) => done({ reply }), (error: unknown) => done({ error }))
      .finally(() => setBusy(false))
  }

  return (
    <div className="space-y-5">
      <SelectionBar />
      <section className="space-y-3">
        <h2 className="text-xl font-bold">{t('chat.title')}</h2>
        {turns.map((turn, i) => (
          <div key={i} className="space-y-2">
            <p className="ms-auto w-fit max-w-[85%] rounded-2xl bg-ink px-4 py-2 text-cotton">{turn.question}</p>
            {turn.reply && (
              <div className="w-fit max-w-[90%] space-y-1 rounded-2xl bg-paper px-4 py-2 shadow-sm">
                {/* Plain text only: the answer is never rendered as HTML. */}
                <p className="whitespace-pre-line">{turn.reply.answer}</p>
                {turn.reply.used_fallback && <p className="text-xs text-slate">{t('chat.fallback')}</p>}
              </div>
            )}
            {turn.error !== undefined && <ErrorBox error={turn.error} />}
          </div>
        ))}
        <form onSubmit={submit} className="space-y-2 rounded-2xl bg-paper p-3 shadow-sm">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={t('chat.placeholder')}
            rows={2}
            aria-label={t('chat.title')}
            className="w-full resize-none rounded-xl border-2 border-line px-3 py-2 focus:border-ink focus:outline-none"
          />
          {tooLong && <p className="text-sm text-madder">{t('chat.tooLong', { max: QUESTION_MAX })}</p>}
          <button
            type="submit"
            disabled={busy || !question.trim() || tooLong}
            className="w-full rounded-xl bg-wheat px-4 py-2.5 text-lg font-bold text-ink disabled:opacity-50"
          >
            {busy ? t('chat.sending') : t('chat.send')}
          </button>
        </form>
      </section>
    </div>
  )
}
