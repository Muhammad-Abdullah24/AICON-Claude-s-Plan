import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, the browser calls /api on the Vite server and Vite forwards it to
// the backend, so there is no CORS to configure locally. In production, set
// VITE_API_BASE_URL to the deployed backend's URL.
const backend = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': backend,
      '/health': backend,
    },
  },
  test: {
    environment: 'node',
  },
})
