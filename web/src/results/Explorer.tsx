import { Play } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { isolateMath } from '../components/ArabicText'
import { afterState, byId, type DotState } from '../components/DotBand'
import { isArabicText, useLang, type Text } from '../i18n'
import type { Arm, Row } from '../lib/types'

type Filter = 'all' | 'fixed' | 'caught' | 'missed' | 'alarm' | 'right' | 'broken'

const FILTERS: { key: Filter; label: Text; dot: string }[] = [
  { key: 'all', label: { en: 'All', ar: 'الكل' }, dot: '' },
  { key: 'fixed', label: { en: 'Fixed by the loop', ar: 'صحّحتها الحلقة' }, dot: 'bg-verified-bright' },
  { key: 'caught', label: { en: 'Caught, still wrong', ar: 'اكتُشفت وبقيت خاطئة' }, dot: 'bg-refuted-bright' },
  { key: 'missed', label: { en: 'Missed', ar: 'فاتت' }, dot: 'ring-2 ring-inset ring-refuted-bright' },
  { key: 'alarm', label: { en: 'False alarm', ar: 'إنذار كاذب' }, dot: 'bg-unknown-bright' },
  { key: 'broken', label: { en: 'Broken', ar: 'أُفسدت' }, dot: 'bg-unknown-bright' },
  { key: 'right', label: { en: 'Right from the start', ar: 'صحيحة من البداية' }, dot: 'bg-ink' },
]

const matches = (f: Filter, s: DotState) => f === 'all' || s === f

export function Explorer({ arm }: { arm: Arm }) {
  const { t } = useLang()
  const [filter, setFilter] = useState<Filter>('all')
  const [all, setAll] = useState(false)
  const rows = useMemo(() => [...arm.rows].sort(byId).map((r) => ({ r, s: afterState(r) })), [arm])
  const counts = useMemo(() => {
    const c: Record<string, number> = { all: rows.length }
    for (const { s } of rows) c[s] = (c[s] ?? 0) + 1
    return c
  }, [rows])
  const shown = rows.filter(({ s }) => matches(filter, s))
  const visible = all ? shown : shown.slice(0, 12)

  return (
    <div>
      <div className="flex flex-wrap gap-2" role="tablist">
        {FILTERS.filter((f) => f.key === 'all' || counts[f.key]).map((f) => (
          <button
            key={f.key}
            type="button"
            role="tab"
            aria-selected={filter === f.key}
            onClick={() => {
              setFilter(f.key)
              setAll(false)
            }}
            className={`press inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[14px] ${
              filter === f.key ? 'border-ink bg-ink text-paper' : 'border-rule text-ink-2 hover:border-rule-strong hover:text-ink'
            }`}
          >
            {f.dot && <span className={`size-2.5 rounded-full ${f.dot}`} />}
            {t(f.label)}
            <span className="num opacity-70">{counts[f.key] ?? 0}</span>
          </button>
        ))}
      </div>

      <div className="mt-6 border-t border-ink">
        <div className="hidden grid-cols-[minmax(0,1fr)_110px_150px_150px_60px_92px] gap-4 border-b border-rule py-3 text-[13px] font-medium text-ink-2 lg:grid">
          <span>{t({ en: 'Question', ar: 'السؤال' })}</span>
          <span>{t({ en: 'Correct', ar: 'الصحيح' })}</span>
          <span>{t({ en: 'First answer', ar: 'الإجابة الأولى' })}</span>
          <span>{t({ en: 'After the loop', ar: 'بعد الحلقة' })}</span>
          <span>{t({ en: 'Rounds', ar: 'جولات' })}</span>
          <span />
        </div>
        <ul>
          {visible.map(({ r }) => (
            <ProblemRow key={r.id} arm={arm} row={r} />
          ))}
        </ul>
        {shown.length === 0 && <p className="py-6 text-[15px] text-ink-3">{t({ en: 'No questions here.', ar: 'لا أسئلة هنا.' })}</p>}
      </div>
      {!all && shown.length > visible.length && (
        <button
          type="button"
          onClick={() => setAll(true)}
          className="press mt-4 rounded-full border border-rule px-4 py-2 text-[14px] font-medium hover:border-ink"
        >
          {t({ en: `Show all ${shown.length}`, ar: `اعرض الكل (${shown.length})` })}
        </button>
      )}
    </div>
  )
}

function Cell({ value, ok, className = '' }: { value: string | null; ok?: boolean; className?: string }) {
  const ar = isArabicText(value)
  return (
    <span
      dir={ar ? 'rtl' : 'ltr'}
      lang={ar ? 'ar' : 'en'}
      className={`line-clamp-2 min-w-0 text-[14px] [overflow-wrap:anywhere] ${ar ? 'font-ar' : ''} ${ok === undefined ? 'text-ink' : ok ? 'text-verified' : 'text-refuted'} ${className}`}
    >
      {value == null ? '—' : ar ? isolateMath(value) : value}
    </span>
  )
}

function ProblemRow({ arm, row }: { arm: Arm; row: Row }) {
  const { t } = useLang()
  const q = arm.problems[row.id] ?? row.id
  const ar = isArabicText(q)
  return (
    <li className="grid gap-x-4 gap-y-2 border-b border-rule py-4 lg:grid-cols-[minmax(0,1fr)_110px_150px_150px_60px_92px] lg:items-center">
      <div className="min-w-0">
        <p dir={ar ? 'rtl' : 'ltr'} lang={ar ? 'ar' : 'en'} className={`line-clamp-2 text-[15px] leading-[1.6] ${ar ? 'font-ar' : ''}`}>
          {ar ? isolateMath(q) : q}
        </p>
        <span className="font-mono text-[12px] text-ink-3">{row.id}</span>
      </div>
      <Label text={t({ en: 'Correct', ar: 'الصحيح' })}>
        <Cell value={row.expected} />
      </Label>
      <Label text={t({ en: 'First answer', ar: 'الإجابة الأولى' })}>
        <Cell value={row.base} ok={row.baseOk} />
      </Label>
      <Label text={t({ en: 'After the loop', ar: 'بعد الحلقة' })}>
        <Cell value={row.final} ok={row.finalOk} />
      </Label>
      <Label text={t({ en: 'Rounds', ar: 'جولات' })}>
        <span className="num text-[14px]">{row.rounds}</span>
      </Label>
      {import.meta.env.VITE_STATIC === '1' ? (
        <span />
      ) : (
        <div>
          <Link
            to={`/demo?trace=${encodeURIComponent(`${arm.key}/${arm.run}/${row.id}`)}`}
            className="press -ms-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1.5 text-[13px] font-medium text-ink-2 hover:bg-panel hover:text-ink"
          >
            <Play size={12} weight="fill" />
            {t({ en: 'Replay', ar: 'إعادة' })}
          </Link>
        </div>
      )}
    </li>
  )
}

function Label({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <div className="flex min-w-0 items-baseline gap-2 lg:block">
      <span className="w-[110px] shrink-0 text-[12.5px] text-ink-3 lg:hidden">{text}</span>
      {children}
    </div>
  )
}
