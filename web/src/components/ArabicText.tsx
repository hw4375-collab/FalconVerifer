import type { ReactNode } from 'react'

// Western-digit equations inside Arabic text keep their left-to-right reading ("59 × 41 = 2419"),
// as Arabic math is usually typeset; the bidi algorithm alone would reverse their order. Each run is
// an inline block so a line break never splits it into two reordered halves.
const MATH = /[(0-9][0-9 ×*+\-−=÷/.%^()²³]*[0-9)²³]|[0-9]/g

export function isolateMath(text: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  for (const m of text.matchAll(MATH)) {
    const start = m.index!
    if (start > last) out.push(text.slice(last, start))
    out.push(
      <bdi key={start} dir="ltr" className="inline-block max-w-full">
        {m[0]}
      </bdi>,
    )
    last = start + m[0].length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}
