import { ArrowRight } from '@phosphor-icons/react'
import { useInView } from 'motion/react'
import { useMemo, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Counter } from '../components/Counter'
import { afterState, DotBand } from '../components/DotBand'
import { Container, Heading } from '../components/Section'
import { useLang } from '../i18n'
import type { Arm } from '../lib/types'

export function Outcome({ arm, scale }: { arm: Arm; scale?: Arm }) {
  const { t } = useLang()
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, amount: 0.45 })
  const head = useRef<HTMLDivElement>(null)
  const headInView = useInView(head, { once: true, amount: 0.6 })
  const s = arm.summary.all
  const counts = useMemo(() => {
    const c = { right: 0, fixed: 0, caught: 0, missed: 0, broken: 0 }
    for (const r of arm.rows) {
      const st = afterState(r)
      if (st === 'right' || st === 'alarm') c.right += 1
      else if (st in c) c[st as keyof typeof c] += 1
    }
    return c
  }, [arm])
  const rows = useMemo(() => arm.rows.map((r) => (r.baseOk && r.finalOk ? { ...r, flagged: false } : r)), [arm])

  return (
    <section className="py-[clamp(96px,14vh,168px)]">
      <Container>
        <div ref={head} className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <Heading className="max-w-[16ch]">{t({ en: 'Same Falcon. Thirty points better.', ar: 'فالكون نفسه، أفضل بثلاثين نقطة.' })}</Heading>
          <div dir="ltr" className="flex items-baseline gap-4 lg:pb-1">
            <span className="text-[clamp(44px,5vw,72px)] font-semibold leading-none tracking-[-0.04em] text-ink-3">
              <Counter to={s.baseline_accuracy * 100} start={headInView} format={(v) => `${Math.round(v)}%`} />
            </span>
            <ArrowRight size={36} weight="regular" className="shrink-0 self-center text-ink-3" aria-hidden />
            <span className="text-[clamp(56px,6.4vw,96px)] font-semibold leading-none tracking-[-0.04em] text-verified">
              <Counter to={s.verified_accuracy * 100} start={headInView} delay={0.5} format={(v) => `${Math.round(v)}%`} />
            </span>
          </div>
        </div>
        <p className="mt-4 text-[17px] text-ink-2">
          {t({
            en: `Accuracy of Falcon-H1-Arabic 3B on the same ${s.n} Arabic questions, before and after the loop.`,
            ar: `دقة Falcon-H1-Arabic 3B على الأسئلة العربية ذاتها (${s.n})، قبل الحلقة وبعدها.`,
          })}
        </p>

        <div ref={ref} className="mt-12">
          <DotBand rows={rows} problems={arm.problems} phase="after" start={inView} />
        </div>

        <ul className="mt-10 grid gap-x-10 gap-y-5 text-[16px] sm:grid-cols-2 lg:grid-cols-4">
          <Key dot="bg-ink" n={counts.right} label={t({ en: 'right from the start', ar: 'صحيحة من البداية' })} />
          <Key dot="bg-verified-bright" n={counts.fixed} label={t({ en: 'fixed after a Lean correction', ar: 'صُحّحت بعد تصحيح Lean' })} strong />
          <Key
            dot="bg-refuted-bright ring-2 ring-offset-2 ring-offset-paper ring-ink"
            n={counts.caught}
            label={t({ en: 'caught, not fixed in 3 rounds', ar: 'اكتُشفت ولم تُصحَّح في 3 جولات' })}
          />
          <Key dot="ring-2 ring-inset ring-refuted-bright" n={counts.missed} label={t({ en: 'missed by Lean', ar: 'فاتت Lean' })} />
        </ul>

        <div className="mt-14 grid gap-8 border-t border-rule pt-10 sm:grid-cols-3">
          <Fact value={`${s.regressions}`} label={t({ en: 'correct answers broken by the loop', ar: 'إجابات صحيحة أفسدتها الحلقة' })} />
          <Fact
            value={`${s.wrong_detected_by_lean}/${s.wrong_baseline}`}
            label={t({ en: 'wrong answers caught by Lean', ar: 'إجابات خاطئة كشفها Lean' })}
          />
          {scale && (
            <Fact
              value={`${Math.round(scale.summary.all.baseline_accuracy * 100)}% → ${Math.round(scale.summary.all.verified_accuracy * 100)}%`}
              label={t({
                en: `on a larger set of ${scale.summary.all.n} generated Arabic questions`,
                ar: `على مجموعة أكبر من ${scale.summary.all.n} سؤالاً عربياً مولّداً`,
              })}
            />
          )}
        </div>

        <Link to="/results" className="press mt-12 inline-flex rounded-full bg-panel px-5 py-3 text-[16px] font-medium hover:bg-rule">
          {t({ en: 'See every result', ar: 'كل النتائج' })}
        </Link>
      </Container>
    </section>
  )
}

function Key({ dot, n, label, strong = false }: { dot: string; n: number; label: string; strong?: boolean }) {
  return (
    <li className="flex items-center gap-3">
      <span className={`size-3.5 shrink-0 rounded-full ${dot}`} />
      <span className={`num text-[22px] font-semibold ${strong ? 'text-verified' : ''}`}>{n}</span>
      <span className="text-ink-2">{label}</span>
    </li>
  )
}

function Fact({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="num text-[clamp(32px,3.2vw,44px)] font-semibold leading-none tracking-[-0.03em]">
        <bdi dir="ltr">{value}</bdi>
      </div>
      <div className="mt-2 max-w-[28ch] text-[15px] text-ink-2">{label}</div>
    </div>
  )
}
