import { useLang } from '../i18n'
import type { Arm } from '../lib/types'
import { SLICES } from './meta'

const pctText = (x: number) => `${Math.round(x * 100)}%`

export function Dumbbells({ arm }: { arm: Arm }) {
  const { t, isAr } = useLang()
  const k = isAr ? 1 : -1
  const rows = SLICES.filter((s) => arm.summary[s.key] && arm.summary[s.key].n >= 5)
  const cols = 'grid-cols-[minmax(0,40%)_1fr] sm:grid-cols-[minmax(0,34%)_1fr_6.75rem]'
  const spacer = <span className="hidden sm:block" />
  const numbers = (a: number, b: number) => (
    <bdi dir="ltr">
      <span className="text-ink-3">{pctText(a)}</span>
      <span className="mx-1.5 text-ink-3">→</span>
      <span className="font-semibold text-ink">{pctText(b)}</span>
    </bdi>
  )
  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-x-5 gap-y-1 text-[13px] text-ink-2">
        <span className="inline-flex items-center gap-2">
          <span className="size-2.5 rounded-full border-2 border-ink-3 bg-paper" />
          {t({ en: 'first answer', ar: 'الإجابة الأولى' })}
        </span>
        <span className="inline-flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-verified-bright" />
          {t({ en: 'after the loop', ar: 'بعد الحلقة' })}
        </span>
      </div>
      <div className="relative">
        <div className={`pointer-events-none absolute inset-0 grid gap-x-4 ${cols}`} aria-hidden>
          <span />
          <div className="relative">
            {[0, 25, 50, 75, 100].map((g) => (
              <span key={g} className="absolute inset-y-0 w-px bg-rule" style={{ insetInlineStart: `${g}%` }} />
            ))}
          </div>
          {spacer}
        </div>
        <ul className="relative space-y-1">
          {rows.map(({ key, label }) => {
            const s = arm.summary[key]
            const a = s.baseline_accuracy * 100
            const b = s.verified_accuracy * 100
            const lo = Math.min(a, b)
            const hi = Math.max(a, b)
            return (
              <li key={key} className={`grid items-center gap-x-4 ${cols}`}>
                <div className="min-w-0 py-1 text-[14px] leading-tight">
                  <div className="text-ink sm:truncate">{t(label)}</div>
                  <div className="num mt-0.5 text-[12.5px] text-ink-3">
                    <span className="sm:hidden">
                      {numbers(s.baseline_accuracy, s.verified_accuracy)}
                      <span className="mx-1.5">·</span>
                    </span>
                    n = {s.n}
                  </div>
                </div>
                <div className="relative h-11">
                  <span
                    className={`absolute top-1/2 h-[2px] -translate-y-1/2 ${b >= a ? 'bg-verified-bright/50' : 'bg-refuted-bright/60'}`}
                    style={{ insetInlineStart: `${lo}%`, width: `${hi - lo}%` }}
                  />
                  <Dot at={a} className="border-2 border-ink-3 bg-paper" />
                  <Dot at={b} className="bg-verified-bright ring-2 ring-paper" />
                </div>
                <div className="num hidden whitespace-nowrap text-end text-[14px] sm:block">{numbers(s.baseline_accuracy, s.verified_accuracy)}</div>
              </li>
            )
          })}
        </ul>
      </div>
      <div className={`grid gap-x-4 ${cols}`} aria-hidden>
        <span />
        <div className="relative mt-1 h-5 text-[12px] text-ink-3">
          {[0, 50, 100].map((g) => (
            <span
              key={g}
              className="num absolute"
              style={{ insetInlineStart: `${g}%`, transform: `translateX(${(g / 100) * k * 100}%)` }}
            >
              {g}%
            </span>
          ))}
        </div>
        {spacer}
      </div>
    </div>
  )
}

function Dot({ at, className }: { at: number; className: string }) {
  return (
    <span
      className={`absolute top-1/2 size-3.5 -translate-y-1/2 rounded-full ${className} -ms-[7px]`}
      style={{ insetInlineStart: `${at}%` }}
    />
  )
}

export function Coverage({ arm }: { arm: Arm }) {
  const { t } = useLang()
  const { steps, finals, rounds } = arm.cot
  const sum = (o: Partial<Record<string, number>>) => Object.values(o).reduce((x, y) => (x ?? 0) + (y ?? 0), 0) ?? 0
  const bars = [
    { label: t({ en: 'Reasoning steps', ar: 'خطوات الاستدلال' }), counts: steps, total: sum(steps) },
    { label: t({ en: 'Final answers', ar: 'الأجوبة النهائية' }), counts: finals, total: rounds },
  ]
  const segs = [
    { key: 'verified', label: t({ en: 'proved', ar: 'مُثبت' }), fill: 'bg-verified-bright' },
    { key: 'refuted', label: t({ en: 'refuted', ar: 'مدحوض' }), fill: 'bg-refuted-bright' },
    { key: 'undecided', label: t({ en: 'undecided', ar: 'غير محسوم' }), fill: 'bg-skip' },
    { key: 'skipped', label: t({ en: 'not checkable', ar: 'غير قابل للفحص' }), fill: 'bg-rule-strong' },
  ]
  const valueOf = (c: Partial<Record<string, number>>, k: string) =>
    k === 'undecided'
      ? (c.unknown ?? 0) + (c.ill_formed ?? 0)
      : k === 'skipped'
        ? (c.skipped ?? 0) + (c.unverified_premise ?? 0)
        : (c[k] ?? 0)

  return (
    <div className="space-y-6">
      {bars.map((b) => {
        const decided = valueOf(b.counts, 'verified') + valueOf(b.counts, 'refuted')
        return (
          <div key={b.label}>
            <div className="flex items-baseline justify-between gap-3 text-[14px]">
              <span className="text-ink">{b.label}</span>
              <span className="text-ink-2">
                {t({ en: 'decided by Lean', ar: 'حسمها Lean' })}{' '}
                <span className="num font-semibold text-ink">{Math.round((decided / Math.max(1, b.total)) * 100)}%</span>
              </span>
            </div>
            <div className="mt-2 flex h-4 gap-[2px]">
              {segs.map((s) => {
                const v = valueOf(b.counts, s.key)
                return v > 0 ? (
                  <span
                    key={s.key}
                    className={`rounded-[4px] ${s.fill}`}
                    style={{ flexGrow: v, flexBasis: 0 }}
                    title={`${s.label}: ${v}`}
                  />
                ) : null
              })}
            </div>
            <div className="num mt-1.5 text-[12.5px] text-ink-3">
              {b.total} {t({ en: 'total', ar: 'المجموع' })}
            </div>
          </div>
        )
      })}
      <ul className="flex flex-wrap gap-x-5 gap-y-1.5 text-[13px] text-ink-2">
        {segs.map((s) => (
          <li key={s.key} className="inline-flex items-center gap-2">
            <span className={`h-2.5 w-4 rounded-[3px] ${s.fill}`} />
            {s.label}
          </li>
        ))}
      </ul>
    </div>
  )
}
