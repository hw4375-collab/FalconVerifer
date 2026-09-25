import { ArrowBendUpLeft } from '@phosphor-icons/react'
import { AnimatePresence, motion, useMotionValueEvent, useReducedMotion, useScroll } from 'motion/react'
import { useId, useRef, useState } from 'react'
import { isolateMath } from '../components/ArabicText'
import { Lean } from '../components/Lean'
import { Container, Heading } from '../components/Section'
import { VerdictBadge } from '../components/Verdict'
import type { Text } from '../i18n'
import { useLang } from '../i18n'
import { useWidth } from '../lib/useWidth'

const EASE = [0.23, 1, 0.32, 1] as const

const STEPS: { title: Text; body: Text }[] = [
  {
    title: { en: 'Falcon answers.', ar: 'فالكون يجيب.' },
    body: {
      en: 'Falcon-H1-Arabic 3B writes its steps in Arabic, then a final answer.',
      ar: 'يكتب Falcon-H1-Arabic 3B خطواته بالعربية، ثم جواباً نهائياً.',
    },
  },
  {
    title: { en: 'Every claim becomes Lean.', ar: 'كل ادعاء يصبح Lean.' },
    body: {
      en: 'Each step, and the final answer, is translated into a Lean 4 proposition.',
      ar: 'تُترجم كل خطوة، والجواب النهائي، إلى قضية في Lean 4.',
    },
  },
  {
    title: { en: 'The kernel decides.', ar: 'النواة تحكم.' },
    body: {
      en: 'Lean tries to prove each claim and its negation. Both steps are proved. The final answer contradicts them.',
      ar: 'يحاول Lean إثبات كل ادعاء ونفيه. تثبت الخطوتان، والجواب النهائي يناقضهما.',
    },
  },
  {
    title: { en: 'Lean teaches, in Arabic.', ar: 'Lean يصحّح، بالعربية.' },
    body: {
      en: 'The refutation goes back to Falcon as a correction in its own language.',
      ar: 'يعود الدحض إلى فالكون تصحيحاً بلغته.',
    },
  },
  {
    title: { en: 'Falcon answers again.', ar: 'فالكون يجيب من جديد.' },
    body: {
      en: 'Round two: 2291. Every claim proved, 41 seconds end to end.',
      ar: 'الجولة الثانية: 2291. كل الادعاءات مُثبتة، خلال 41 ثانية.',
    },
  },
]

export function Loop() {
  const { t } = useLang()
  const [step, setStep] = useState(0)
  const captions = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: captions, offset: ['start center', 'end center'] })
  useMotionValueEvent(scrollYProgress, 'change', (p) => {
    const next = Math.max(0, Math.min(STEPS.length - 1, Math.floor(p * STEPS.length)))
    setStep((s) => (s === next ? s : next))
  })

  return (
    <section className="relative py-[clamp(72px,10vh,128px)]">
      <Container>
        <Heading>{t({ en: 'Every step goes to the kernel.', ar: 'كل خطوة تمرّ على النواة.' })}</Heading>
      </Container>

      <Container className="mt-4 hidden lg:grid lg:grid-cols-12 lg:gap-12">
        <div ref={captions} className="lg:col-span-4">
          {STEPS.map((s, i) => (
            <Caption key={i} active={step === i} title={t(s.title)} body={t(s.body)} />
          ))}
        </div>
        <div className="lg:col-span-8">
          <div className="sticky top-[calc(4rem+8vh)] pt-2">
            <LoopFigure step={step} />
          </div>
        </div>
      </Container>

      <Container className="mt-10 flex flex-col gap-14 lg:hidden">
        {STEPS.map((s, i) => (
          <div key={i}>
            <h3 className="text-[26px] font-semibold tracking-[-0.02em]">{t(s.title)}</h3>
            <p className="mt-2 text-[17px] leading-[1.5] text-ink-2">{t(s.body)}</p>
            <div className="mt-5">
              <LoopFigure step={i} />
            </div>
          </div>
        ))}
      </Container>
    </section>
  )
}

function Caption({ active, title, body }: { active: boolean; title: string; body: string }) {
  const tone = 'transition-colors duration-500'
  return (
    <div className="flex min-h-[72vh] items-center">
      <div className={`border-s-2 ps-5 ${tone} ${active ? 'border-ink' : 'border-rule'}`}>
        <h3 className={`text-[clamp(26px,2.3vw,34px)] font-semibold leading-[1.1] tracking-[-0.025em] ${tone} ${active ? 'text-ink' : 'text-ink-3'}`}>
          {title}
        </h3>
        <p className={`mt-3 max-w-[34ch] text-[18px] leading-[1.5] ${tone} ${active ? 'text-ink-2' : 'text-ink-3'}`}>{body}</p>
      </div>
    </div>
  )
}

const CLAIMS = [
  { ar: 'العدد الإجمالي للتمرات = 59 × 41 = 2419 تمرة', lean: '(59:ℕ) * 41 = 2419' },
  { ar: 'التميرات المتبقية = 2419 - 128 = 2291 تمرة', lean: '2419 - 128 = 2291' },
]

export function LoopFigure({ step }: { step: number }) {
  const { t, isAr } = useLang()
  const reveal = (visible: boolean, delay = 0) => ({
    initial: false as const,
    animate: visible ? { opacity: 1, x: 0, filter: 'blur(0px)', transitionEnd: { filter: 'none' } } : { opacity: 0, x: isAr ? 8 : -8, filter: 'blur(3px)' },
    transition: { duration: 0.45, delay: visible ? delay : 0, ease: EASE },
  })
  const final2 = step >= 4

  return (
    <figure className="rounded-[var(--radius-panel)] bg-panel p-5 sm:p-8">
      <Cycle step={step} />

      <div className="mt-6 space-y-2">
        {CLAIMS.map((c, i) => (
          <ClaimRow key={i} dim={step === 3}>
            <p lang="ar" dir="rtl" className="font-ar text-[17px] leading-[1.6] text-ink">
              {isolateMath(c.ar)}
            </p>
            <motion.div {...reveal(step >= 1, 0.08 * i)} className="text-[15px]">
              <Lean>{c.lean}</Lean>
            </motion.div>
            <motion.div {...reveal(step >= 2, 0.1 + 0.12 * i)} className="justify-self-start md:justify-self-end">
              <VerdictBadge verdict="verified" />
            </motion.div>
          </ClaimRow>
        ))}
        <ClaimRow highlight={step >= 2 && step < 4 ? 'refuted' : final2 ? 'verified' : undefined}>
          <p lang="ar" dir="rtl" className="font-ar text-[17px] leading-[1.6] text-ink">
            الجواب النهائي:{' '}
            <AnimatePresence mode="popLayout" initial={false}>
              <motion.span
                key={final2 ? 'a2' : 'a1'}
                initial={{ opacity: 0, y: 6, filter: 'blur(3px)' }}
                animate={{ opacity: 1, y: 0, filter: 'blur(0px)', transitionEnd: { filter: 'none' } }}
                exit={{ opacity: 0, y: -6, filter: 'blur(3px)' }}
                transition={{ duration: 0.35, ease: EASE }}
                className={`inline-block font-semibold ${final2 ? 'text-verified' : step >= 2 ? 'text-refuted' : ''}`}
              >
                <bdi dir="ltr">{final2 ? '2291' : '187'}</bdi> تمرة
              </motion.span>
            </AnimatePresence>
          </p>
          <motion.div {...reveal(step >= 1, 0.16)} className="text-[15px]">
            <Lean>{'(59:ℕ) * 41 - 128 = 2291'}</Lean>
          </motion.div>
          <motion.div {...reveal(step >= 2, 0.36)} className="justify-self-start md:justify-self-end">
            {final2 ? (
              <VerdictBadge verdict="verified" />
            ) : (
              <VerdictBadge verdict="refuted" label={t({ en: '187 ≠ 2291', ar: '187 ≠ 2291' })} />
            )}
          </motion.div>
        </ClaimRow>
      </div>

      <AnimatePresence initial={false}>
        {step === 3 && (
          <motion.div
            key="feedback"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.45, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="mt-5 rounded-xl border border-rule bg-paper p-5">
              <div className="flex items-center gap-2 text-[14px] font-medium text-refuted">
                <ArrowBendUpLeft size={16} weight="bold" />
                {t({ en: 'Lean 4 to Falcon', ar: 'من Lean 4 إلى فالكون' })}
              </div>
              <p lang="ar" dir="rtl" className="mt-3 font-ar text-[17px] leading-[1.8] text-ink">
                الجواب النهائي لا يطابق ما تستنتجه خطواتك. تحقق Lean 4 من{' '}
                <code dir="ltr" className="font-mono text-[15px]">
                  (59:ℕ) * 41 - 128 = 2291
                </code>
                ؛ يجب أن يكون الرقم بعد «الجواب النهائي» هو نتيجة هذا الحساب.
              </p>
              {!isAr && (
                <p className="mt-2 text-[14px] leading-snug text-ink-3">
                  Your final answer does not match what your steps derive. Lean 4 verified the computation; the
                  number after “final answer” must be its result.
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        initial={false}
        animate={{ opacity: final2 ? 1 : 0 }}
        transition={{ duration: 0.4, delay: final2 ? 0.3 : 0 }}
        className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-1 text-[14px] text-ink-2"
        aria-hidden={!final2}
      >
        <span>{t({ en: 'Round 2', ar: 'الجولة 2' })}</span>
        <span className="num">41 s</span>
        <span>{t({ en: 'assurance 1.0', ar: 'درجة الضمان 1.0' })}</span>
      </motion.div>
    </figure>
  )
}

function ClaimRow({
  children,
  dim = false,
  highlight,
}: {
  children: React.ReactNode
  dim?: boolean
  highlight?: 'refuted' | 'verified'
}) {
  const ring =
    highlight === 'refuted'
      ? 'bg-refuted-wash/70'
      : highlight === 'verified'
        ? 'bg-verified-wash/70'
        : 'bg-paper/0'
  return (
    <div
      className={`grid items-center gap-x-5 gap-y-1 rounded-xl px-3 py-2.5 transition-[background-color,opacity] duration-500 md:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_auto] ${ring} ${dim ? 'opacity-45' : ''}`}
    >
      {children}
    </div>
  )
}

function Cycle({ step }: { step: number }) {
  const { t } = useLang()
  const reduce = useReducedMotion()
  const [ref, width] = useWidth<HTMLDivElement>()
  const head = `head${useId().replace(/[^\w-]/g, '')}`
  const W = Math.round(Math.max(300, Math.min(640, width || 640)))
  const L = W < 480 ? 60 : 76
  const R = W - L
  const a = L + 38
  const b = R - 38
  const c = (b - a) * 0.28
  const top = `M${a} 78 C ${a + c} 22, ${b - c} 22, ${b} 78`
  const bottom = `M${b} 118 C ${b - c} 174, ${a + c} 174, ${a} 118`

  const topActive = step === 1 || step === 4
  const bottomActive = step === 3
  const falconActive = step === 0 || step === 4
  const leanTone = step === 2 || step === 3 ? 'refuted' : step === 4 ? 'verified' : 'ink'
  const edge = (active: boolean, tone: string) => (active ? `var(--color-${tone})` : 'var(--color-rule-strong)')
  const topTone = step === 4 ? 'verified' : 'ink'

  return (
    <div ref={ref}>
      <svg
        viewBox={`0 0 ${W} 214`}
        className="block h-auto w-full [direction:ltr]"
        role="img"
        aria-label={t({ en: 'Falcon and the Lean kernel', ar: 'فالكون ونواة Lean' })}
      >
        <defs>
          {['ink', 'refuted', 'verified', 'rule'].map((k) => (
            <marker key={k} id={`${head}-${k}`} viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path
                d="M1 1 L8 5 L1 9"
                fill="none"
                stroke={k === 'rule' ? 'var(--color-rule-strong)' : `var(--color-${k})`}
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </marker>
          ))}
        </defs>

        <path
          d={top}
          fill="none"
          strokeWidth="2"
          stroke={edge(topActive, topTone)}
          markerEnd={`url(#${head}-${topActive ? topTone : 'rule'})`}
          style={{ transition: 'stroke 400ms ease' }}
        />
        <path
          d={bottom}
          fill="none"
          strokeWidth="2"
          stroke={edge(bottomActive, 'refuted')}
          markerEnd={`url(#${head}-${bottomActive ? 'refuted' : 'rule'})`}
          style={{ transition: 'stroke 400ms ease' }}
        />
        {!reduce && topActive && <Packet key={top} d={top} tone={topTone} />}
        {!reduce && bottomActive && <Packet key={bottom} d={bottom} tone="refuted" />}

        <circle
          cx={L}
          cy="98"
          r="30"
          fill="var(--color-panel)"
          strokeWidth="2.5"
          stroke={falconActive ? 'var(--color-ink)' : 'var(--color-rule-strong)'}
          style={{ transition: 'stroke 400ms ease' }}
        />
        <text x={L} y="107" textAnchor="middle" className="fill-ink font-ar text-[24px] font-semibold">
          ف
        </text>
        <circle
          cx={R}
          cy="98"
          r="30"
          style={{ transition: 'fill 400ms ease' }}
          fill={leanTone === 'ink' ? 'var(--color-ink)' : `var(--color-${leanTone})`}
        />
        <path d={`M${R - 8} 84 v28 M${R - 8} 98 h18`} stroke="var(--color-paper)" strokeWidth="3.2" strokeLinecap="round" />

        <text x={W / 2} y="14" textAnchor="middle" className="fill-ink-3 text-[14px]">
          {t({ en: 'translate to Lean', ar: 'ترجمة إلى Lean' })}
        </text>
        <text x={W / 2} y="206" textAnchor="middle" className="fill-ink-3 text-[14px]">
          {t({ en: 'correction', ar: 'تصحيح' })}
        </text>
        <text x={L} y="156" textAnchor="middle" className="fill-ink-2 text-[14px] font-medium">
          {t({ en: 'Falcon', ar: 'فالكون' })}
        </text>
        <text x={R} y="156" textAnchor="middle" className="fill-ink-2 text-[14px] font-medium">
          {t({ en: 'Lean 4 kernel', ar: 'نواة Lean 4' })}
        </text>
      </svg>
    </div>
  )
}

function Packet({ d, tone }: { d: string; tone: string }) {
  return (
    <motion.path
      d={d}
      pathLength={1}
      fill="none"
      stroke={`var(--color-${tone})`}
      strokeWidth="5"
      strokeLinecap="round"
      strokeDasharray="0.06 1"
      initial={{ strokeDashoffset: 0.06 }}
      animate={{ strokeDashoffset: -1 }}
      transition={{ duration: 1.5, repeat: Infinity, ease: 'linear', repeatDelay: 0.2 }}
    />
  )
}
