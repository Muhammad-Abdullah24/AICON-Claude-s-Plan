import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router'

import { api } from './api/client'
import { AppShell } from './components/shell/AppShell'
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

// Screens laid out in two columns on a desktop get the wide frame; the rest stay at a comfortable reading width.
const WIDE = new Set(['/', '/why'])

export default function App() {
  const [meta, reload] = useAsync((signal) => api.meta(signal), 'meta')

  if (meta.status !== 'ok') {
    return (
      <main className="mx-auto max-w-xl px-4 py-10">
        {meta.status === 'error' ? <ErrorBox error={meta.error} onRetry={reload} /> : <Loading />}
      </main>
    )
  }

  return (
    <AppStateProvider meta={meta.data}>
      <AppShell>
        <Main>
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
        </Main>
      </AppShell>
    </AppStateProvider>
  )
}

function Main({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  return (
    <main className={`mx-auto w-full px-4 py-6 sm:px-6 lg:px-8 lg:py-8 ${WIDE.has(pathname) ? 'max-w-6xl' : 'max-w-3xl'}`}>
      {children}
    </main>
  )
}
