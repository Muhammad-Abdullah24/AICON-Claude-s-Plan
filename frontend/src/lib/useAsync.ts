import { useCallback, useEffect, useState } from 'react'

export type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'ok'; data: T }
  | { status: 'error'; error: unknown }

type Settled<T> = Exclude<AsyncState<T>, { status: 'loading' }>

/**
 * Loads data whenever `key` changes, e.g. `${crop}|${mandi}`.
 *
 * Each result is tagged with the key that produced it, so a slow old response
 * can never show up under newer inputs, and "loading" is simply "no result
 * for the current key yet". `reload` retries.
 */
export function useAsync<T>(load: (signal: AbortSignal) => Promise<T>, key: string) {
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<{ key: string; state: Settled<T> } | null>(null)
  const current = `${key}#${attempt}`

  useEffect(() => {
    const ctrl = new AbortController()
    load(ctrl.signal).then(
      (data) => setResult({ key: current, state: { status: 'ok', data } }),
      (error: unknown) => {
        if (!ctrl.signal.aborted) setResult({ key: current, state: { status: 'error', error } })
      },
    )
    return () => ctrl.abort()
    // `load` is a new function every render; `current` captures everything it depends on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current])

  const reload = useCallback(() => setAttempt((n) => n + 1), [])
  const state: AsyncState<T> = result?.key === current ? result.state : { status: 'loading' }
  return [state, reload] as const
}
