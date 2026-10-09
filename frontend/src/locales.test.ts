import { describe, expect, it } from 'vitest'

import en from './locales/en.json'
import ur from './locales/ur.json'

function keys(obj: object, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === 'object' ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  )
}

function values(obj: object): string[] {
  return Object.values(obj).flatMap((v) => (v && typeof v === 'object' ? values(v) : [String(v)]))
}

describe('translations', () => {
  it('Urdu and English have exactly the same keys', () => {
    expect(keys(ur).sort()).toEqual(keys(en).sort())
  })

  it('no string is empty', () => {
    for (const v of [...values(ur), ...values(en)]) expect(v.trim()).not.toBe('')
  })

  it('placeholders match between languages', () => {
    const vars = (s: string) => (s.match(/{{\w+}}/g) ?? []).sort()
    const flatEn = Object.fromEntries(keys(en).map((k) => [k, k.split('.').reduce<any>((o, p) => o[p], en)]))
    for (const k of keys(ur)) {
      const u = k.split('.').reduce<any>((o, p) => o[p], ur) as string
      expect(vars(u), k).toEqual(vars(flatEn[k]))
    }
  })

  it('Urdu strings are written in Urdu script', () => {
    const urduish = /[؀-ۿ]/
    const exceptions = new Set(['lang.switchTo', 'lang.switchLabel']) // these name the other language
    for (const k of keys(ur)) {
      if (exceptions.has(k)) continue
      const u = k.split('.').reduce<any>((o, p) => o[p], ur) as string
      expect(urduish.test(u), k).toBe(true)
    }
  })
})
