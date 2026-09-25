import { useMemo, useRef, useState } from 'react'
import { useLang } from '../i18n'
import type { Row } from '../lib/types'

export type DotState = 'idle' | 'right' | 'wrong' | 'fixed' | 'caught' | 'missed' | 'alarm' | 'broken'

export function afterState(r: Row): DotState {
  if (r.baseOk && r.finalOk) return r.flagged ? 'alarm' : 'right'
  if (!r.baseOk && r.finalOk) return 'fixed'
  if (!r.baseOk) return r.flagged ? 'caught' : 'missed'
  return 'broken'
}

const DOT: Record<DotState, string> = {
  idle: 'bg-transparent ring-1 ring-inset ring-rule-strong',
  right: 'bg-ink',
  wrong: 'bg-refuted-bright',
  fixed: 'bg-verified-bright',
  caught: 'bg-refuted-bright ring-2 ring-offset-2 ring-offset-paper ring-ink',
  missed: 'bg-transparent ring-2 ring-inset ring-refuted-bright',
  alarm: 'bg-ink ring-2 ring-offset-2 ring-offset-paper ring-unknown-bright',
  broken: 'bg-refuted-bright ring-2 ring-offset-2 ring-offset-paper ring-unknown-bright',
}

export const byId = (a: Row, b: Row) => a.id.localeCompare(b.id, 'en', { numeric: true })

const dotTransition = (delay: number) =>
  `background-color 520ms var(--ease-out-strong) ${delay}ms, box-shadow 520ms var(--ease-out-strong) ${delay}ms, transform 160ms var(--ease-out-strong) 0ms`

export function DotBand({
  rows,
  problems,
  phase,
  start,
  cols = 'grid-cols-[repeat(12,minmax(0,1fr))] sm:grid-cols-[repeat(18,minmax(0,1fr))] lg:grid-cols-[repeat(29,minmax(0,1fr))]',
}: {
  rows: Row[]
  problems: Record<string, string>
  phase: 'baseline' | 'after'
  start: boolean
  cols?: string
}) {
  const { t } = useLang()
  const ordered = useMemo(() => [...rows].sort(byId), [rows])
  const changing = useMemo(() => {
    const m = new Map<string, number>()
    let k = 0
    for (const r of ordered) if (afterState(r) !== (r.baseOk ? 'right' : 'wrong')) m.set(r.id, k++)
    return m
  }, [ordered])
  const box = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<{ i: number; x: number; y: number; w: number } | null>(null)

  const stateOf = (r: Row): DotState => {
    if (phase === 'baseline') return start ? (r.baseOk ? 'right' : 'wrong') : 'idle'
    return start ? afterState(r) : r.baseOk ? 'right' : 'wrong'
  }
  const delayOf = (r: Row, i: number) =>
    phase === 'baseline' ? i * 16 : changing.has(r.id) ? 300 + changing.get(r.id)! * 55 : 0

  const show = (i: number, el: HTMLElement) => {
    const b = box.current?.getBoundingClientRect()
    const d = el.getBoundingClientRect()
    if (b) setTip({ i, x: d.left - b.left + d.width / 2, y: d.top - b.top, w: b.width })
  }
  const r = tip ? ordered[tip.i] : null
  const left = tip ? Math.min(Math.max(tip.x, 170), tip.w - 170) : 0

  return (
    <div ref={box} className="relative" onMouseLeave={() => setTip(null)}>
      <div className={`grid gap-x-[6px] gap-y-[10px] sm:gap-x-[8px] ${cols}`}>
        {ordered.map((row, i) => {
          const s = stateOf(row)
          return (
            <button
              key={row.id}
              type="button"
              aria-label={`${row.id}: ${problems[row.id] ?? ''}`}
              onMouseEnter={(e) => show(i, e.currentTarget)}
              onFocus={(e) => show(i, e.currentTarget)}
              onBlur={() => setTip(null)}
              className="group flex aspect-square items-center justify-center rounded-full outline-offset-1"
            >
              <span
                className={`block size-[72%] rounded-full group-hover:scale-110 ${DOT[s]}`}
                style={{ transition: dotTransition(delayOf(row, i)) }}
              />
            </button>
          )
        })}
      </div>

      {r && tip && (
        <div
          className="pointer-events-none absolute z-20 w-[320px] -translate-x-1/2 -translate-y-[calc(100%+14px)] rounded-xl border border-rule bg-paper p-4 shadow-[var(--shadow-float)]"
          style={{ left, top: tip.y }}
          role="tooltip"
        >
          <p lang="ar" dir="auto" className="line-clamp-3 text-[15px] leading-[1.6] text-ink">
            {problems[r.id]}
          </p>
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[13px]">
            <dt className="text-ink-3">{t({ en: 'Falcon', ar: 'فالكون' })}</dt>
            <dd dir="auto" className={r.baseOk ? 'text-ink' : 'text-refuted'}>
              {r.base ?? t({ en: 'no final answer', ar: 'لا جواب نهائي' })}
            </dd>
            {phase === 'after' && (
              <>
                <dt className="text-ink-3">{t({ en: 'After Lean', ar: 'بعد Lean' })}</dt>
                <dd dir="auto" className={r.finalOk ? 'text-verified' : 'text-refuted'}>
                  {r.final ?? t({ en: 'no final answer', ar: 'لا جواب نهائي' })}
                </dd>
              </>
            )}
            <dt className="text-ink-3">{t({ en: 'Correct', ar: 'الصحيح' })}</dt>
            <dd dir="auto" className="text-ink">
              {r.expected}
            </dd>
          </dl>
        </div>
      )}
    </div>
  )
}
