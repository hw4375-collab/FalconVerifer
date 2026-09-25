import { ArrowRight } from '@phosphor-icons/react'
import { motion, useInView, useReducedMotion } from 'motion/react'
import { useRef } from 'react'
import { Link } from 'react-router-dom'
import { Counter } from '../components/Counter'
import { Lean } from '../components/Lean'
import { Container, Heading, Lede } from '../components/Section'
import { VerdictBadge } from '../components/Verdict'
import { ORG, ORG_URL } from '../components/Mark'
import { REPO_URL } from '../components/Nav'
import { useLang } from '../i18n'
import { BASE } from '../lib/data'

const EASE = [0.23, 1, 0.32, 1] as const

export function Lesson() {
  const { t, isAr } = useLang()
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, amount: 0.4 })
  const reduce = !!useReducedMotion()
  const show = (delay: number, x = 0) => ({
    initial: reduce ? false : { opacity: 0, x: isAr ? -x : x, filter: 'blur(4px)' },
    animate: inView ? { opacity: 1, x: 0, filter: 'blur(0px)', transitionEnd: { filter: 'none' } } : {},
    transition: { duration: 0.6, delay: reduce ? 0 : delay, ease: EASE },
  })

  return (
    <section className="py-[clamp(96px,14vh,168px)]">
      <Container>
        <Heading>{t({ en: 'Every correction is a lesson.', ar: 'كل تصحيح درس.' })}</Heading>
        <Lede className="mt-5">
          {t({
            en: 'A refuted answer, its proved fix and the Lean evidence between them make a training pair. Next, Falcon learns from them.',
            ar: 'الإجابة المدحوضة وتصحيحها المُثبت ودليل Lean بينهما تشكّل زوجاً للتدريب. الخطوة التالية: أن يتعلّم فالكون منها.',
          })}
        </Lede>

        <div ref={ref} className="mt-14 grid items-center gap-6 lg:grid-cols-[minmax(0,1.25fr)_auto_minmax(0,0.8fr)_auto_minmax(0,0.9fr)]">
          <motion.div {...show(0)} className="rounded-[var(--radius-panel)] bg-panel p-6">
            <PairRow verdict="refuted" label={t({ en: 'rejected', ar: 'مرفوضة' })} answer="187 تمرة" />
            <div className="my-3 h-px bg-rule" />
            <PairRow verdict="verified" label={t({ en: 'chosen', ar: 'مختارة' })} answer="2291 تمرة" />
            <div className="mt-4 text-[14px] text-ink-3">
              <span className="me-2">{t({ en: 'evidence', ar: 'الدليل' })}</span>
              <Lean>{'(59:ℕ) * 41 - 128 = 2291'}</Lean>
            </div>
          </motion.div>

          <Arrow show={show(0.5)} />

          <motion.div {...show(0.7, -12)} className="relative mx-auto w-full max-w-[280px] lg:max-w-none">
            <div className="absolute inset-0 translate-x-3 translate-y-3 rounded-[var(--radius-panel)] border border-rule bg-paper" />
            <div className="absolute inset-0 translate-x-1.5 translate-y-1.5 rounded-[var(--radius-panel)] border border-rule bg-paper" />
            <div className="relative rounded-[var(--radius-panel)] border border-rule-strong bg-paper p-6">
              <div className="text-[clamp(44px,4.4vw,60px)] font-semibold leading-none tracking-[-0.04em]">
                <Counter to={294} start={inView} delay={0.8} duration={1.4} />
              </div>
              <div className="mt-2 text-[15px] text-ink-2">{t({ en: 'training pairs so far', ar: 'زوجاً للتدريب حتى الآن' })}</div>
              <div className="mt-4 flex gap-5 text-[14px]">
                <span>
                  <span className="num font-semibold">226</span> {t({ en: 'Arabic', ar: 'بالعربية' })}
                </span>
                <span>
                  <span className="num font-semibold">68</span> {t({ en: 'English', ar: 'بالإنجليزية' })}
                </span>
              </div>
            </div>
          </motion.div>

          <Arrow show={show(1.2)} dashed />

          <motion.div
            {...show(1.4, -12)}
            className="rounded-[var(--radius-panel)] border-2 border-dashed border-rule-strong p-6"
          >
            <div className="text-[22px] font-semibold tracking-[-0.02em]">
              {t({ en: 'Next: fine-tune', ar: 'التالي: تدريب' })} <span className="whitespace-nowrap">Falcon-H1-Arabic</span>
            </div>
            <div className="mt-1 text-[15px] text-ink-2">
              {t({ en: 'on its own proved corrections', ar: 'على تصحيحاته المُثبتة' })}
            </div>
          </motion.div>
        </div>
      </Container>
    </section>
  )
}

function PairRow({ verdict, label, answer }: { verdict: 'refuted' | 'verified'; label: string; answer: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="text-[14px] font-medium text-ink-2">{label}</span>
      <span className="flex items-center gap-3">
        <span lang="ar" dir="rtl" className={`font-ar text-[20px] font-semibold ${verdict === 'refuted' ? 'text-refuted' : 'text-verified'}`}>
          {answer}
        </span>
        <VerdictBadge verdict={verdict} />
      </span>
    </div>
  )
}

function Arrow({ show, dashed = false }: { show: object; dashed?: boolean }) {
  return (
    <motion.div {...show} className={`flex justify-center ${dashed ? 'text-ink-3' : 'text-ink-2'}`}>
      <ArrowRight size={30} weight="regular" className="rotate-90 lg:rotate-0 rtl:lg:rotate-180" aria-hidden />
    </motion.div>
  )
}

export function Org() {
  const { t } = useLang()
  return (
    <section className="border-t border-rule bg-panel/60 py-[clamp(64px,10vh,120px)]">
      <Container className="flex flex-col items-center gap-8 text-center md:flex-row md:text-start">
        <a href={ORG_URL} target="_blank" rel="noreferrer" className="press shrink-0">
          <img src={`${BASE}brand/chaosbutterfly-logo.png`} alt={ORG} className="h-[120px] w-auto md:h-[150px]" />
        </a>
        <div className="max-w-[60ch]">
          <p className="text-[13px] uppercase tracking-[0.14em] text-ink-2">
            {t({ en: 'A ChaosButterfly.org project', ar: 'مشروع من ChaosButterfly.org' })}
          </p>
          <h2 className="mt-2 text-[clamp(26px,3.2vw,40px)] font-semibold leading-[1.1] tracking-[-0.03em]">
            {t({
              en: 'We build the trust layer for Arabic AI.',
              ar: 'نبني طبقة الثقة للذكاء الاصطناعي العربي.',
            })}
          </h2>
          <p className="mt-4 text-[17px] leading-[1.55] text-ink-2">
            {t({
              en: 'ChaosButterfly puts machine-checked proof between language models and the people who rely on them. NYU Falcon is our first product: a Lean 4 audit layer for Falcon, TII’s Arabic-native model — zero fine-tuning, one kernel process, every verdict auditable.',
              ar: 'تضع ChaosButterfly البرهان الآلي بين النماذج اللغوية ومن يعتمدون عليها. NYU Falcon أول منتجاتنا: طبقة تدقيق بـ Lean 4 فوق Falcon، نموذج معهد الابتكار التكنولوجي العربي — بلا ضبط دقيق، بعملية نواة واحدة، وكل حكم قابل للتدقيق.',
            })}
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3 md:justify-start">
            <a href={ORG_URL} target="_blank" rel="noreferrer" className="press rounded-full border border-ink px-5 py-2.5 text-[15px] font-medium text-ink hover:bg-ink hover:text-paper">
              chaosbutterfly.org ↗
            </a>
            <a href={REPO_URL} target="_blank" rel="noreferrer" className="press rounded-full px-5 py-2.5 text-[15px] font-medium text-ink hover:bg-panel">
              {t({ en: 'Open source on GitHub', ar: 'مفتوح المصدر على GitHub' })}
            </a>
          </div>
        </div>
      </Container>
    </section>
  )
}

export function Close() {
  const { t } = useLang()
  return (
    <section className="py-[clamp(96px,16vh,200px)]">
      <Container className="flex flex-col items-center text-center">
        <h2 className="max-w-[18ch] text-[clamp(40px,5.6vw,84px)] font-semibold leading-[1.02] tracking-[-0.038em]">
          {t({ en: 'Put a question to Falcon.', ar: 'اطرح سؤالاً على فالكون.' })}
        </h2>
        <div className="mt-10 flex flex-wrap justify-center gap-3">
          <Link to="/demo" className="press rounded-full bg-ink px-6 py-3 text-[16px] font-medium text-paper hover:bg-[#2a2d31]">
            {t({ en: 'Open the demo', ar: 'افتح التجربة' })}
          </Link>
          <Link to="/results" className="press rounded-full px-5 py-3 text-[16px] font-medium text-ink hover:bg-panel">
            {t({ en: 'See the results', ar: 'شاهد النتائج' })}
          </Link>
        </div>
      </Container>
    </section>
  )
}
