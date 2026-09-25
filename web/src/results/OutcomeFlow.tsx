import { useMemo, useState } from 'react'
import { useLang, type Text } from '../i18n'
import type { Arm } from '../lib/types'

type Seg = { key: string; n: number; label: Text; fill: string; ink: string }

export function outcomeCounts(arm: Arm) {
  const c = { right: 0, wrong: 0, clean: 0, alarm: 0, caught: 0, missed: 0, kept: 0, broken: 0, fixedC: 0, stuckC: 0, fixedM: 0, stuckM: 0 }
  for (const r of arm.rows) {
    if (r.baseOk) {
      c.right++
      if (r.flagged) c.alarm++
      else c.clean++
      if (r.finalOk) c.kept++
      else c.broken++
    } else {
      c.wrong++
      if (r.flagged) {
        c.caught++
        if (r.finalOk) c.fixedC++
        else c.stuckC++
      } else {
        c.missed++
        if (r.finalOk) c.fixedM++
        else c.stuckM++
      }
    }
  }
  return c
}

export function OutcomeFlow({ arm }: { arm: Arm }) {
  const { t } = useLang()
  const c = useMemo(() => outcomeCounts(arm), [arm])
  const n = arm.rows.length
  const [tip, setTip] = useState<{ seg: Seg; row: string } | null>(null)

  const rows: { title: Text; segs: Seg[] }[] = [
    {
      title: { en: 'First answer', ar: 'الإجابة الأولى' },
      segs: [
        { key: 'right', n: c.right, label: { en: 'right', ar: 'صحيحة' }, fill: 'bg-ink', ink: 'text-paper' },
        { key: 'wrong', n: c.wrong, label: { en: 'wrong', ar: 'خاطئة' }, fill: 'bg-refuted-bright', ink: 'text-paper' },
      ],
    },
    {
      title: { en: 'Lean’s check', ar: 'فحص Lean' },
      segs: [
        { key: 'clean', n: c.clean, label: { en: 'not flagged', ar: 'لم تُعلَّم' }, fill: 'bg-ink', ink: 'text-paper' },
        { key: 'alarm', n: c.alarm, label: { en: 'false alarm', ar: 'إنذار كاذب' }, fill: 'bg-unknown-bright', ink: 'text-paper' },
        { key: 'caught', n: c.caught, label: { en: 'caught', ar: 'اكتُشفت' }, fill: 'bg-refuted-bright', ink: 'text-paper' },
        { key: 'missed', n: c.missed, label: { en: 'missed', ar: 'فاتت' }, fill: 'bg-refuted-bright/35', ink: 'text-ink' },
      ],
    },
    {
      title: { en: 'After the loop', ar: 'بعد الحلقة' },
      segs: [
        { key: 'kept', n: c.kept, label: { en: 'still right', ar: 'بقيت صحيحة' }, fill: 'bg-ink', ink: 'text-paper' },
        { key: 'broken', n: c.broken, label: { en: 'broken', ar: 'أُفسدت' }, fill: 'bg-unknown-bright', ink: 'text-paper' },
        { key: 'fixedC', n: c.fixedC, label: { en: 'fixed', ar: 'صُحّحت' }, fill: 'bg-verified-bright', ink: 'text-paper' },
        { key: 'stuckC', n: c.stuckC, label: { en: 'still wrong', ar: 'بقيت خاطئة' }, fill: 'bg-refuted-bright', ink: 'text-paper' },
        { key: 'fixedM', n: c.fixedM, label: { en: 'fixed', ar: 'صُحّحت' }, fill: 'bg-verified-bright', ink: 'text-paper' },
        { key: 'stuckM', n: c.stuckM, label: { en: 'still wrong', ar: 'بقيت خاطئة' }, fill: 'bg-refuted-bright/35', ink: 'text-ink' },
      ],
    },
  ]

  return (
    <div className="relative">
      <div className="space-y-3">
        {rows.map((row) => (
          <div key={row.title.en} className="grid gap-2 md:grid-cols-[150px_1fr] md:items-center md:gap-5">
            <div className="text-[14px] font-medium text-ink-2">{t(row.title)}</div>
            <div className="flex h-12 gap-[2px]">
              {row.segs
                .filter((s) => s.n > 0)
                .map((s) => {
                  const share = s.n / n
                  const wide = share * 100 > 13
                  return (
                    <button
                      key={s.key}
                      type="button"
                      onMouseEnter={() => setTip({ seg: s, row: t(row.title) })}
                      onMouseLeave={() => setTip(null)}
                      onFocus={() => setTip({ seg: s, row: t(row.title) })}
                      onBlur={() => setTip(null)}
                      aria-label={`${t(row.title)}: ${s.n} ${t(s.label)}`}
                      className={`flex min-w-[8px] items-center justify-center overflow-visible rounded-[4px] px-2 transition-opacity hover:opacity-85 ${s.fill} ${s.ink}`}
                      style={{ flexGrow: s.n, flexBasis: 0 }}
                    >
                      {share * 100 > 5 && (
                        <span className="whitespace-nowrap text-[14px] font-semibold">
                          <span className="num">{s.n}</span>
                          {wide && <span className="ms-1.5 font-normal opacity-85">{t(s.label)}</span>}
                        </span>
                      )}
                    </button>
                  )
                })}
            </div>
          </div>
        ))}
      </div>
      {tip && (
        <div className="pointer-events-none absolute end-0 top-[-12px] z-10 -translate-y-full rounded-xl border border-rule bg-paper px-3.5 py-2.5 text-[14px] shadow-[var(--shadow-float)]">
          <div className="num text-[18px] font-semibold">
            {tip.seg.n} <span className="text-[14px] font-normal text-ink-2">{t(tip.seg.label)}</span>
          </div>
          <div className="text-[13px] text-ink-3">
            {tip.row} · {Math.round((tip.seg.n / n) * 1000) / 10}%
          </div>
        </div>
      )}
    </div>
  )
}
