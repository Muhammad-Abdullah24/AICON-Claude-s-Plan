import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router'

import { api } from './api/client'
import { Header } from './components/Header'
import { ReplayBanner } from './components/ReplayBanner'
import { ErrorBox, Loading } from './components/Status'
import { useAsync } from './lib/useAsync'
import { Chat } from './pages/Chat'
import { Compare } from './pages/Compare'
import { Grow } from './pages/Grow'
import { Home } from './pages/Home'
import { Margin } from './pages/Margin'
import { Profile } from './pages/Profile'
import { AppStateProvider } from './state'

// The chart library is large: load it only when a chart screen opens, so Home stays fast on mobile data.
const Why = lazy(() => import('./pages/Why').then((m) => ({ default: m.Why })))
const History = lazy(() => import('./pages/History').then((m) => ({ default: m.History })))

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
      <ReplayBanner />
      <main className="mx-auto max-w-xl px-4 py-5">
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/why" element={<Why />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/grow" element={<Grow />} />
            <Route path="/history" element={<History />} />
            <Route path="/margin" element={<Margin />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
    </AppStateProvider>
  )
}
