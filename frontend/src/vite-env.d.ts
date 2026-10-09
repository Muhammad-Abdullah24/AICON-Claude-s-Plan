/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Deployed backend URL, e.g. https://farmsight-api.example.com. Empty in dev (Vite proxies /api). */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
