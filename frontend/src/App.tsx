import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router'

import { api } from './api/client'
import { Header } from './components/Header'
import { ErrorBox, Loading } from './components/Status'
import { useAsync } from './lib/useAsync'
import { Ask } from './pages/Ask'
import { AppStateProvider } from './state'

// The chart library is large: load it only when the Forecast screen opens, so the
// Ask screen stays fast on mobile data.
const Forecast = lazy(() => import('./pages/Forecast').then((m) => ({ default: m.Forecast })))

export default function App() {
  const [meta, reload] = useAsync((signal) => api.meta(signal), 'meta')

  if (meta.status !== 'ok') {
    return (
      <main className="mx-auto max-w-xl p-4">
        {meta.status === 'error' ? <ErrorBox error={meta.error} onRetry={reload} /> : <Loading />}
      </main>
    )
  }

  return (
    <AppStateProvider meta={meta.data}>
      <Header />
      <main className="mx-auto max-w-xl px-4 py-5">
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<Ask />} />
            <Route path="/forecast" element={<Forecast />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
    </AppStateProvider>
  )
}
