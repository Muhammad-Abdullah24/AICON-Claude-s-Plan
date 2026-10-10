import '@fontsource/noto-nastaliq-urdu/arabic-400.css'
import '@fontsource/noto-nastaliq-urdu/arabic-700.css'
import '@fontsource/ibm-plex-sans/latin-400.css'
import '@fontsource/ibm-plex-sans/latin-600.css'
import '@fontsource/ibm-plex-mono/latin-500.css'
import './index.css'
import './i18n'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router'

import App from './App'
import { Kasht } from './pages/Kasht'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/* KASHT is a self-contained WhatsApp-style demo: no backend, so it sits outside the app shell. */}
        <Route path="/kasht" element={<Kasht />} />
        <Route path="/*" element={<App />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
