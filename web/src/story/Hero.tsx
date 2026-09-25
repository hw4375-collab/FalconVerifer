import { ArrowCounterClockwise } from '@phosphor-icons/react'
import { motion, useReducedMotion } from 'motion/react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Lean } from '../components/Lean'
import { Turnstile } from '../components/Mark'
import { Container } from '../components/Section'
import { VerdictBadge } from '../components/Verdict'
import { useLang } from '../i18n'

const EASE = [0.23, 1, 0.32, 1] as const
const EASE_IN_OUT = [0.77, 0, 0.175, 1] as const

export function Hero() {
  const { t } = useLang()
  return (
    <section className="relative">
      <Container className="grid min-h-[calc(100dvh-4rem)] items-center gap-12 pb-16 pt-10 lg:grid-cols-12 lg:gap-10 lg:pb-20 lg:pt-12">
        <div className="lg:col-span-5">
          <h1 className="text-[clamp(44px,5.4vw,78px)] font-semibold leading-[1.02] tracking-[-0.038em]">
            {t({ en: 'Falcon speaks Arabic.', ar: 'فالكون يتكلّم العربية.' })}
            <br />
            {t({ en: 'Lean checks its reasoning.', ar: 'وLean يتحقّق من منطقه.' })}
          </h1>
          <p className="mt-6 max-w-[40ch] text-[clamp(17px,1.45vw,20px)] leading-[1.5] text-ink-2">
            {t({
              en: 'Every step becomes a Lean 4 proposition. The kernel proves or refutes it, and each refutation teaches Falcon.',
              ar: 'تتحوّل كل خطوة إلى قضية في Lean 4. تُثبتها النواة أو تدحضها، وكل دحضٍ يصبح درساً لفالكون.',
            })}
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Link
              to="/demo"
              className="press rounded-full bg-ink px-6 py-3 text-[16px] font-medium text-paper hover:bg-[#2a2d31]"
            >
              {t({ en: 'Open the demo', ar: 'افتح التجربة' })}
            </Link>
            <Link to="/results" className="press rounded-full px-5 py-3 text-[16px] font-medium text-ink hover:bg-panel">
              {t({ en: 'See the results', ar: 'شاهد النتائج' })}
            </Link>
          </div>
        </div>
        <div className="lg:col-span-7">
          <HeroFigure />
        </div>
      </Container>
    </section>
  )
}

function HeroFigure() {
  const { t, isAr } = useLang()
  const reduce = !!useReducedMotion()
  const [run, setRun] = useState(0)
  const at = (s: number) => (reduce ? 0 : s)
  const enter = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 10, filter: 'blur(4px)' },
    animate: { opacity: 1, y: 0, filter: 'blur(0px)', transitionEnd: { filter: 'none' } },
    transition: { duration: 0.6, delay: at(delay), ease: EASE },
  })

  return (
    <figure key={run} className="relative rounded-[var(--radius-panel)] bg-panel px-6 py-7 sm:px-10 sm:py-9">
      <button
        type="button"
        onClick={() => setRun((r) => r + 1)}
        className="press absolute end-3 top-3 rounded-full p-2 text-ink-3 hover:bg-paper hover:text-ink"
        aria-label={t({ en: 'Replay', ar: 'أعد التشغيل' })}
      >
        <ArrowCounterClockwise size={18} />
      </button>

      <p lang="ar" dir="rtl" className="font-ar text-[clamp(19px,1.7vw,24px)] leading-[1.75] text-ink">
        اشترى حمدان ٥٩ علبة تحتوي كل منها على ٤١ تمرة، ثم أعطى ١٢٨ تمرة من مجموعها لأصدقائه. كم تمرة بقي لدى حمدان؟
      </p>
      {!isAr && (
        <p className="mt-2 text-[14px] leading-snug text-ink-3">
          Hamdan buys 59 boxes of 41 dates, then gives 128 dates to friends. How many are left?
        </p>
      )}

      <ol className="mt-8">
        <Row node="falcon" nodeAt={at(0.35)} lineAt={at(0.7)} reduce={reduce}>
          <motion.div {...enter(0.35)}>
            <Who>Falcon-H1-Arabic 3B</Who>
            <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-2">
              <Struck at={at(1.75)} reduce={reduce}>
                <Answer value="187" />
              </Struck>
              <motion.span {...enter(1.95)}>
                <VerdictBadge verdict="refuted" />
              </motion.span>
            </div>
          </motion.div>
        </Row>

        <Row node="lean" nodeAt={at(1.05)} lineAt={at(2.2)} reduce={reduce}>
          <motion.div {...enter(1.05)}>
            <Who>{t({ en: 'Lean 4 kernel', ar: 'نواة Lean 4' })}</Who>
            <div className="mt-2 text-[clamp(16px,1.5vw,20px)]">
              <Lean>{'(59:ℕ) * 41 - 128 = 2291'}</Lean>
            </div>
            <p className="mt-1 text-[14px] text-ink-3">
              {t({ en: 'Falcon’s own steps give 2291, not 187.', ar: 'خطوات فالكون نفسها تعطي 2291 لا 187.' })}
            </p>
          </motion.div>
        </Row>

        <Row node="proved" nodeAt={at(2.6)} reduce={reduce} last>
          <motion.div {...enter(2.6)}>
            <Who>{t({ en: 'Falcon, after one correction', ar: 'فالكون، بعد تصحيح واحد' })}</Who>
            <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-2">
              <Answer value="2291" className="text-verified" />
              <motion.span {...enter(3.0)}>
                <VerdictBadge verdict="verified" />
              </motion.span>
            </div>
          </motion.div>
        </Row>
      </ol>
    </figure>
  )
}

function Answer({ value, className = '' }: { value: string; className?: string }) {
  return (
    <span dir="rtl" lang="ar" className={`inline-flex items-baseline gap-2 font-ar ${className}`}>
      <span className="num text-[clamp(44px,4.4vw,64px)] font-semibold leading-none tracking-[-0.03em]">{value}</span>
      <span className="text-[20px]">تمرة</span>
    </span>
  )
}

function Who({ children }: { children: ReactNode }) {
  return <div className="text-[14px] font-medium text-ink-2">{children}</div>
}

function Row({
  node,
  nodeAt,
  lineAt = 0,
  reduce,
  last = false,
  children,
}: {
  node: 'falcon' | 'lean' | 'proved'
  nodeAt: number
  lineAt?: number
  reduce: boolean
  last?: boolean
  children: ReactNode
}) {
  return (
    <li className="grid grid-cols-[22px_1fr] gap-x-5">
      <div className="relative flex justify-center">
        {!last && (
          <motion.span
            aria-hidden
            className="absolute bottom-0 top-[26px] w-[2px] origin-top rounded-full bg-rule-strong"
            initial={reduce ? false : { scaleY: 0 }}
            animate={{ scaleY: 1 }}
            transition={{ duration: 0.5, delay: lineAt, ease: EASE_IN_OUT }}
          />
        )}
        <motion.span
          className="relative mt-[1px]"
          initial={reduce ? false : { scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.4, delay: nodeAt, ease: EASE }}
        >
          {node === 'falcon' && <span className="block size-[16px] rounded-full border-2 border-ink bg-panel" />}
          {node === 'lean' && (
            <span className="flex size-[22px] items-center justify-center rounded-full bg-ink text-paper">
              <Turnstile className="size-[13px]" />
            </span>
          )}
          {node === 'proved' && <span className="block size-[16px] rounded-full bg-verified-bright" />}
        </motion.span>
      </div>
      <div className={last ? '' : 'pb-8'}>{children}</div>
    </li>
  )
}

function Struck({ children, at, reduce }: { children: ReactNode; at: number; reduce: boolean }) {
  return (
    <span className="relative inline-block">
      <motion.span
        className="inline-block"
        initial={reduce ? false : { opacity: 1 }}
        animate={{ opacity: 0.4 }}
        transition={{ duration: 0.3, delay: at }}
      >
        {children}
      </motion.span>
      <motion.span
        aria-hidden
        className="absolute inset-x-[-6px] top-[50%] h-[4px] origin-[0%_50%] rounded-full bg-refuted-bright"
        initial={reduce ? false : { scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ duration: 0.45, delay: at, ease: EASE_IN_OUT }}
      />
    </span>
  )
}
