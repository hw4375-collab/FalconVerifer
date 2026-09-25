import { motion } from 'motion/react'
import { useSearchParams } from 'react-router-dom'
import { Container } from '../components/Section'
import { useLang } from '../i18n'
import { loadBench, modelLabel, useAsync } from '../lib/data'
import type { Arm } from '../lib/types'
import { Coverage, Dumbbells } from '../results/Charts'
import { Explorer } from '../results/Explorer'
import { armSet } from '../results/meta'
import { OutcomeFlow, outcomeCounts } from '../results/OutcomeFlow'

const EASE = [0.23, 1, 0.32, 1] as const
const pct = (x: number) => `${Math.round(x * 100)}%`

export default function Results() {
  const { t } = useLang()
  const { data } = useAsync(loadBench)
  const [params, setParams] = useSearchParams()
  const arms = data?.arms ?? []
  const key = params.get('run') ?? 'falcon3b_arabic'
  const arm = arms.find((a) => a.key === key) ?? arms[0]

  return (
    <main className="pb-24">
      <Container className="pt-12 md:pt-16">
        <h1 className="text-[clamp(40px,5vw,68px)] font-semibold leading-[1.02] tracking-[-0.035em]">
          {t({ en: 'Results', ar: 'النتائج' })}
        </h1>
        <p className="mt-4 max-w-[62ch] text-[17px] leading-[1.55] text-ink-2">
          {t({
            en: 'Each run scores Falcon’s first answer and its answer after the verify-and-teach loop, on the same questions, against the same correct answers.',
            ar: 'كل تشغيل يقيّم إجابة فالكون الأولى وإجابته بعد حلقة التحقق والتعليم، على الأسئلة ذاتها، مقابل الأجوبة الصحيحة ذاتها.',
          })}
        </p>
      </Container>

      {arms.length > 0 && (
        <Container className="mt-10">
          <RunPicker arms={arms} value={arm?.key} onChange={(k) => setParams({ run: k }, { replace: true })} />
        </Container>
      )}

      {arm && (
        <motion.div key={arm.key} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35, ease: EASE }}>
          <Headline arm={arm} />

          <Container className="mt-16">
            <SectionTitle>{t({ en: 'Where the answers went', ar: 'إلى أين ذهبت الإجابات' })}</SectionTitle>
            <div className="mt-8">
              <OutcomeFlow arm={arm} />
            </div>
            <Kpis arm={arm} />
          </Container>

          <Container className="mt-20 grid gap-16 lg:grid-cols-2 lg:gap-14">
            <div>
              <SectionTitle>{t({ en: 'By kind of question', ar: 'بحسب نوع السؤال' })}</SectionTitle>
              <div className="mt-8">
                <Dumbbells arm={arm} />
              </div>
            </div>
            <div>
              <SectionTitle>{t({ en: 'How much Lean could decide', ar: 'ما استطاع Lean حسمه' })}</SectionTitle>
              <div className="mt-8">
                <Coverage arm={arm} />
              </div>
            </div>
          </Container>

          <Container className="mt-20">
            <SectionTitle>{t({ en: 'Every question', ar: 'كل سؤال' })}</SectionTitle>
            <div className="mt-8">
              <Explorer arm={arm} />
            </div>
          </Container>

          <Container className="mt-16">
            <p className="max-w-[68ch] text-[14px] leading-[1.6] text-ink-3">
              {t({
                en: `Run ${arm.run}. Student ${modelLabel(arm.student)}, formalizer ${modelLabel(arm.formalizer)}, up to ${arm.maxRounds} rounds, Lean 4 with Mathlib. The first answer is round 1 of the same trace; answers are graded by exact match with the correct answer. Caught means Lean refuted a claim in the first answer. Source: bench/results/${arm.key}.`,
                ar: `التشغيل ${arm.run}. الطالب ${modelLabel(arm.student)}، والمُصيغ ${modelLabel(arm.formalizer)}، حتى ${arm.maxRounds} جولات، مع Lean 4 وMathlib. الإجابة الأولى هي الجولة الأولى من المسار نفسه؛ وتُقيَّم الإجابات بالمطابقة التامة مع الجواب الصحيح. «اكتُشفت» تعني أن Lean دحض ادعاءً في الإجابة الأولى. المصدر: bench/results/${arm.key}.`,
              })}
            </p>
          </Container>
        </motion.div>
      )}
    </main>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-[clamp(24px,2.4vw,32px)] font-semibold tracking-[-0.025em]">{children}</h2>
}

function RunPicker({ arms, value, onChange }: { arms: Arm[]; value?: string; onChange: (k: string) => void }) {
  const { t } = useLang()
  const groups = [
    { title: t({ en: 'Arabic questions', ar: 'أسئلة عربية' }), items: arms.filter((a) => a.lang === 'ar') },
    { title: t({ en: 'English questions', ar: 'أسئلة إنجليزية' }), items: arms.filter((a) => a.lang === 'en') },
  ]
  return (
    <div className="space-y-6" role="radiogroup" aria-label={t({ en: 'Benchmark run', ar: 'تشغيل المعيار' })}>
      {groups.map((g) => (
        <div key={g.title}>
          <div className="mb-2.5 text-[13px] font-medium text-ink-3">{g.title}</div>
          <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-5">
            {g.items.map((a) => {
              const s = a.summary.all
              const active = a.key === value
              return (
                <button
                  key={a.key}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => onChange(a.key)}
                  className={`press rounded-2xl border p-3.5 text-start ${active ? 'border-ink bg-paper' : 'border-rule hover:border-rule-strong'}`}
                >
                  <div className="truncate text-[14px] font-semibold">{modelLabel(a.student)}</div>
                  <div className="truncate text-[13px] text-ink-2">
                    {armSet(a, t)}, {s.n}
                  </div>
                  <div className="num mt-2 text-[15px]">
                    <bdi dir="ltr">
                      <span className="text-ink-3">{pct(s.baseline_accuracy)}</span>
                      <span className="mx-1 text-ink-3">→</span>
                      <span className="font-semibold text-verified">{pct(s.verified_accuracy)}</span>
                    </bdi>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

function Headline({ arm }: { arm: Arm }) {
  const { t } = useLang()
  const s = arm.summary.all
  const gain = Math.round((s.verified_accuracy - s.baseline_accuracy) * 1000) / 10
  return (
    <Container className="mt-14 border-t border-rule pt-12">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-[15px] text-ink-2">
            {modelLabel(arm.student)}, {armSet(arm, t)}
          </div>
          <div className="mt-3 flex items-baseline gap-4" dir="ltr">
            <span className="text-[clamp(44px,5vw,72px)] font-semibold leading-none tracking-[-0.04em] text-ink-3">{pct(s.baseline_accuracy)}</span>
            <span className="text-[32px] text-ink-3">→</span>
            <span className="text-[clamp(56px,6.4vw,96px)] font-semibold leading-none tracking-[-0.04em] text-verified">{pct(s.verified_accuracy)}</span>
          </div>
        </div>
        <p className="max-w-[36ch] text-[16px] leading-[1.55] text-ink-2">
          {t({
            en: `Accuracy on ${s.n} questions, ${gain >= 0 ? '+' : ''}${gain} points after the loop, averaging ${s.mean_rounds} rounds and ${Math.round(s.mean_latency_s)} s per question.`,
            ar: `الدقة على ${s.n} سؤالاً، بفارق ${gain >= 0 ? '+' : ''}${gain} نقطة بعد الحلقة، بمتوسط ${s.mean_rounds} جولة و${Math.round(s.mean_latency_s)} ثانية لكل سؤال.`,
          })}
        </p>
      </div>
    </Container>
  )
}

function Kpis({ arm }: { arm: Arm }) {
  const { t } = useLang()
  const c = outcomeCounts(arm)
  const items = [
    { label: t({ en: 'Wrong answers caught', ar: 'إجابات خاطئة اكتُشفت' }), value: `${c.caught}/${c.wrong}` },
    { label: t({ en: 'Wrong answers fixed', ar: 'إجابات خاطئة صُحّحت' }), value: `${c.fixedC + c.fixedM}/${c.wrong}` },
    { label: t({ en: 'False alarms on right answers', ar: 'إنذارات كاذبة على إجابات صحيحة' }), value: `${c.alarm}/${c.right}` },
    { label: t({ en: 'Right answers broken', ar: 'إجابات صحيحة أُفسدت' }), value: `${c.broken}` },
  ]
  return (
    <dl className="mt-10 grid grid-cols-2 gap-x-8 gap-y-6 border-t border-rule pt-8 lg:grid-cols-4">
      {items.map((i) => (
        <div key={i.label}>
          <dt className="text-[14px] text-ink-2">{i.label}</dt>
          <dd className="mt-1 text-[clamp(28px,2.8vw,40px)] font-semibold leading-none tracking-[-0.03em]">
            <bdi dir="ltr">{i.value}</bdi>
          </dd>
        </div>
      ))}
    </dl>
  )
}
