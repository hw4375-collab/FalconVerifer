import type { ReactNode } from 'react'

const TOKEN = /(\d+(?:\.\d+)?|[ℕℤℚℝ]|Fin|Bool|true|false|[∀∃¬→↔∧∨∣≠≤≥=<>⊢×*+\-/^]|[()[\],:])/g

function tone(tok: string): string | undefined {
  if (/^\d/.test(tok)) return 'text-ink'
  if (/^[ℕℤℚℝ]$|^Fin$|^Bool$/.test(tok)) return 'text-ink-3'
  if (/^[∀∃¬→↔∧∨∣≠≤≥=<>⊢×*+\-/^]$/.test(tok)) return 'text-ink-2'
  if (/^[()[\],:]$/.test(tok)) return 'text-ink-3'
  return undefined
}

export function leanTokens(src: string): ReactNode[] {
  const out: ReactNode[] = []
  let last = 0
  for (const m of src.matchAll(TOKEN)) {
    if (m.index! > last) out.push(src.slice(last, m.index))
    out.push(
      <span key={m.index} className={tone(m[0])}>
        {m[0]}
      </span>,
    )
    last = m.index! + m[0].length
  }
  if (last < src.length) out.push(src.slice(last))
  return out
}

export function Lean({ children, className = '' }: { children: string; className?: string }) {
  return (
    <code dir="ltr" className={`font-mono text-[0.92em] leading-relaxed break-words text-ink ${className}`}>
      {leanTokens(children)}
    </code>
  )
}
