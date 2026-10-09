import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import ur from './locales/ur.json'

export const LANGS = ['ur', 'en'] as const
export type Lang = (typeof LANGS)[number]

const STORAGE_KEY = 'farmsight.lang'

function savedLang(): Lang {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    return v === 'en' ? 'en' : 'ur'
  } catch {
    return 'ur' // storage blocked (private mode, previews): fall back to the default
  }
}

/** Keeps <html lang dir> in step with the language, so the whole layout mirrors. */
function applyToDocument(lang: string) {
  document.documentElement.lang = lang
  document.documentElement.dir = lang === 'ur' ? 'rtl' : 'ltr'
  try {
    localStorage.setItem(STORAGE_KEY, lang)
  } catch {
    // not fatal: the language just won't be remembered
  }
}

i18n.on('languageChanged', applyToDocument)

void i18n.use(initReactI18next).init({
  resources: { ur: { translation: ur }, en: { translation: en } },
  lng: savedLang(),
  fallbackLng: 'ur',
  interpolation: { escapeValue: false }, // React already escapes
  returnNull: false,
})

applyToDocument(i18n.language)

export default i18n
