import { useInView } from 'motion/react'
import { useRef } from 'react'
import { Counter } from '../components/Counter'
import { DotBand } from '../components/DotBand'
import { Container, Heading, Lede } from '../components/Section'
import { useLang } from '../i18n'
import type { Arm } from '../lib/types'

export function Problem({ arm }: { arm: Arm }) {
  const { t } = useLang()
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, amount: 0.45 })
  const right = arm.rows.filter((r) => r.baseOk).length
  const wrong = arm.rows.length - right

  return (
    <section className="py-[clamp(96px,14vh,168px)]">
      <Container>
        <Heading>{t({ en: 'Fluent Arabic. Wrong answers.', ar: 'عربية سليمة. إجابات خاطئة.' })}</Heading>
        <Lede className="mt-5">
          {t({
            en: `Falcon-H1-Arabic 3B on ${arm.rows.length} Arabic math and logic questions. Each dot is one question, colored by its first answer.`,
            ar: `نموذج Falcon-H1-Arabic 3B أمام ${arm.rows.length} سؤالاً عربياً في الرياضيات والمنطق. كل نقطة سؤال، ولونها بحسب إجابته الأولى.`,
          })}
        </Lede>

        <div ref={ref} className="mt-14">
          <DotBand rows={arm.rows} problems={arm.problems} phase="baseline" start={inView} />
        </div>

        <div className="mt-10 flex flex-wrap gap-x-16 gap-y-6">
          <Tally tone="bg-ink" label={t({ en: 'right', ar: 'صحيحة' })}>
            <Counter to={right} start={inView} delay={0.2} />
          </Tally>
          <Tally tone="bg-refuted-bright" label={t({ en: 'wrong', ar: 'خاطئة' })} strong>
            <Counter to={wrong} start={inView} delay={0.2} />
          </Tally>
        </div>
      </Container>
    </section>
  )
}

function Tally({
  tone,
  label,
  strong = false,
  children,
}: {
  tone: string
  label: string
  strong?: boolean
  children: React.ReactNode
}) {
  return (
    <div className="flex items-baseline gap-3">
      <span className={`size-3 self-center rounded-full ${tone}`} />
      <span
        className={`text-[clamp(40px,4.2vw,64px)] font-semibold leading-none tracking-[-0.03em] ${strong ? 'text-refuted' : 'text-ink'}`}
      >
        {children}
      </span>
      <span className="text-[18px] text-ink-2">{label}</span>
    </div>
  )
}
