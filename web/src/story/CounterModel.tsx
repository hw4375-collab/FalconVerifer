import { motion, useInView, useReducedMotion } from 'motion/react'
import { useRef } from 'react'
import { Container, Heading, Lede } from '../components/Section'
import { VerdictBadge } from '../components/Verdict'
import { useLang } from '../i18n'
import { useWidth } from '../lib/useWidth'

const EASE = [0.23, 1, 0.32, 1] as const
const DRAW = [0.77, 0, 0.175, 1] as const

export function CounterModel() {
  const { t, isAr } = useLang()
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, amount: 0.45 })
  const reduce = !!useReducedMotion()
  const at = (s: number) => (reduce ? 0 : s)
  const show = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 8, filter: 'blur(3px)' },
    animate: inView ? { opacity: 1, y: 0, filter: 'blur(0px)', transitionEnd: { filter: 'none' } } : {},
    transition: { duration: 0.55, delay: at(delay), ease: EASE },
  })

  return (
    <section className="py-[clamp(96px,14vh,168px)]">
      <Container>
        <Heading>{t({ en: 'When the logic breaks, Lean shows where.', ar: 'حين ينكسر المنطق، يُريك Lean أين.' })}</Heading>
        <Lede className="mt-5">
          {t({
            en: 'Falcon-H1 7B answered yes. Lean refutes it with a world where both premises hold and the conclusion fails.',
            ar: 'أجاب Falcon-H1 7B بنعم. فيدحض Lean ذلك بعالمٍ تصحّ فيه المقدمتان وتسقط النتيجة.',
          })}
        </Lede>

        <div ref={ref} className="mt-14 grid gap-10 lg:grid-cols-12 lg:gap-12">
          <div className="space-y-7 lg:col-span-5">
            <motion.div {...show(0)}>
              <p lang="ar" dir="rtl" className="font-ar text-[clamp(19px,1.7vw,23px)] leading-[1.75]">
                كل الأطباء متعلمون، وبعض المتعلمين فقراء. هل يلزم أن بعض الأطباء فقراء؟
              </p>
              {!isAr && (
                <p className="mt-1 text-[14px] text-ink-3">
                  All doctors are educated, and some educated people are poor. Must some doctors be poor?
                </p>
              )}
            </motion.div>

            <motion.div {...show(0.35)} className="flex items-center gap-4">
              <span className="w-[132px] shrink-0 text-[14px] font-medium text-ink-2">Falcon-H1 7B</span>
              <span lang="ar" className="font-ar text-[30px] font-semibold text-refuted">
                نعم
              </span>
              <motion.span {...show(2.6)}>
                <VerdictBadge verdict="refuted" />
              </motion.span>
            </motion.div>

            <motion.div {...show(2.0)} className="flex items-start gap-4">
              <span className="w-[132px] shrink-0 pt-1 text-[14px] font-medium text-ink-2">
                {t({ en: 'Lean 4 counter-example', ar: 'مثال Lean 4 المضاد' })}
              </span>
              <div lang="ar" dir="rtl" className="font-ar text-[16px] leading-[1.9]">
                <div>
                  «الأطباء» = <span dir="ltr" className="font-mono">{'{x0}'}</span>
                </div>
                <div>
                  «متعلمون» = <span dir="ltr" className="font-mono">{'{x0, x1}'}</span>
                </div>
                <div>
                  «فقراء» = <span dir="ltr" className="font-mono">{'{x1}'}</span>
                </div>
              </div>
            </motion.div>

            <motion.div {...show(3.2)} className="flex items-center gap-4">
              <span className="w-[132px] shrink-0 text-[14px] font-medium text-ink-2">
                {t({ en: 'Falcon, corrected', ar: 'فالكون، بعد التصحيح' })}
              </span>
              <span lang="ar" className="font-ar text-[30px] font-semibold text-verified">
                لا
              </span>
              <VerdictBadge verdict="verified" />
            </motion.div>
          </div>

          <div className="lg:col-span-7">
            <div className="rounded-[var(--radius-panel)] bg-panel p-4 sm:p-8">
              <Euler play={inView} at={at} />
            </div>
          </div>
        </div>
      </Container>
    </section>
  )
}

function Euler({ play, at }: { play: boolean; at: (s: number) => number }) {
  const { isAr } = useLang()
  const [ref, width] = useWidth<HTMLDivElement>()
  // viewBox units per CSS pixel: labels never render below a readable pixel size on narrow screens
  const k = 560 / Math.max(260, width || 560)
  const size = (units: number, px: number) => Math.max(units, px * k)
  const ar = size(19, 14)
  const en = size(14, 12)
  const fade = (delay: number) => ({
    initial: { opacity: 0 },
    animate: play ? { opacity: 1 } : {},
    transition: { duration: 0.4, delay: at(delay) },
  })

  const circle = (cx: number, cy: number, r: number, delay: number, stroke: string) => (
    <motion.circle
      cx={cx}
      cy={cy}
      r={r}
      fill="none"
      stroke={stroke}
      strokeWidth="2"
      initial={{ pathLength: 0, opacity: 0 }}
      animate={play ? { pathLength: 1, opacity: 1 } : {}}
      transition={{ duration: 0.9, delay: at(delay), ease: DRAW }}
    />
  )
  const label = (x: number, y: number, text: string, gloss: string, strong = false) => (
    <motion.g {...fade(1.2)}>
      <text x={x} y={y} textAnchor="middle" className={`font-ar ${strong ? 'fill-ink font-semibold' : 'fill-ink-2'}`} style={{ fontSize: ar }}>
        {text}
      </text>
      {!isAr && (
        <text x={x} y={y + ar} textAnchor="middle" className="fill-ink-3" style={{ fontSize: en }}>
          {gloss}
        </text>
      )}
    </motion.g>
  )
  const dot = (cx: number, cy: number, name: string, delay: number) => (
    <motion.g
      initial={{ opacity: 0, scale: 0.6 }}
      animate={play ? { opacity: 1, scale: 1 } : {}}
      transition={{ duration: 0.4, delay: at(delay), ease: EASE }}
      style={{ transformOrigin: `${cx}px ${cy}px` }}
    >
      <circle cx={cx} cy={cy} r={size(7, 5)} className="fill-ink" />
      <text x={cx + size(13, 9)} y={cy + size(6, 4.5)} className="fill-ink font-mono" style={{ fontSize: size(16, 12) }}>
        {name}
      </text>
    </motion.g>
  )

  return (
    <div ref={ref}>
      <svg viewBox="0 0 560 366" className="block h-auto w-full [direction:ltr]" role="img" aria-label="Counter-example">
        {circle(236, 196, 156, 0.2, 'var(--color-ink-2)')}
        {circle(170, 204, 72, 0.55, 'var(--color-ink)')}
        {circle(392, 196, 108, 0.9, 'var(--color-ink-2)')}
        {label(236, 84, 'متعلمون', 'educated')}
        {label(170, 180, 'الأطباء', 'doctors', true)}
        {label(452, 180, 'فقراء', 'poor')}
        {dot(170, 238, 'x0', 1.6)}
        {dot(334, 196, 'x1', 1.8)}
        {dot(488, 336, 'x2', 2.0)}
      </svg>
      <motion.div {...fade(2.5)} className="mt-3 text-center">
        <p lang="ar" dir="rtl" className="font-ar text-[16px] text-refuted">
          النتيجة «بعض الأطباء فقراء» خاطئة هنا
        </p>
        {!isAr && <p className="mt-0.5 text-[13px] text-ink-3">“Some doctors are poor” is false in this world.</p>}
      </motion.div>
    </div>
  )
}
