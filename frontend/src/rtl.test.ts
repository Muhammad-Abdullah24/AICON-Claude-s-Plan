/**
 * Guards the right-to-left layout. Physical left/right utilities do not mirror
 * when the page switches to Urdu, so only logical ones (ms-, me-, ps-, pe-,
 * start-, end-, text-start, text-end) are allowed in components.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

import { describe, expect, it } from 'vitest'

const PHYSICAL =
  /(?<![\w-])(?:-?(?:ml|mr|pl|pr|left|right|border-l|border-r|rounded-l|rounded-r|rounded-tl|rounded-tr|rounded-bl|rounded-br|scroll-ml|scroll-mr)-[\w./[\]-]+|text-left|text-right|float-left|float-right)(?![\w-])/g

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) return files(p)
    return /\.tsx$/.test(name) ? [p] : []
  })
}

describe('RTL safety', () => {
  it('components use only logical (start/end) spacing and alignment', () => {
    const offenders: string[] = []
    for (const f of files(join(import.meta.dirname, '.'))) {
      for (const [i, line] of readFileSync(f, 'utf8').split('\n').entries()) {
        for (const m of line.matchAll(PHYSICAL)) offenders.push(`${f}:${i + 1}  ${m[0]}`)
      }
    }
    expect(offenders).toEqual([])
  })
})
