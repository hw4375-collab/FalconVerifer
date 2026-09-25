import { ArrowCounterClockwise } from '@phosphor-icons/react'
import { motion, useInView, useReducedMotion } from 'motion/react'
import { useRef, useState } from 'react'
import { Lean } from '../components/Lean'
import { Container, Heading, Lede } from '../components/Section'
import { useLang } from '../i18n'
import { useWidth } from '../lib/useWidth'

const EASE = [0.23, 1, 0.32, 1] as const
const DRAW = [0.77, 0, 0.175, 1] as const

// arabic.parse("٥٩ × ٤١ يساوي ٢٤١٩"): word types n | nʳ n nˡ | n | nʳ s nˡ | n, planar links
// (0,1) (3,4) (2,5) (7,8) over the flat type string; the uncancelled s is the sentence.
const WORDS = [
  { text: '٥٩', types: ['n'] },
  { text: '×', types: ['nʳ', 'n', 'nˡ'] },
  { text: '٤١', types: ['n'] },
  { text: 'يساوي', types: ['nʳ', 's', 'nˡ'] },
  { text: '٢٤١٩', types: ['n'] },
]
const CUPS: [number, number, number][] = [
  [0, 1, 44],
  [3, 4, 44],
  [2, 5, 96],
  [7, 8, 44],
]
const S = 6

// Drawn at its rendered width (300 to 746 px), so the type labels stay legible on a phone.
function layout(width: number) {
  const W = Math.round(Math.max(300, Math.min(746, width || 746)))
  const p = (W - 300) / 446
  const v = 0.75 + 0.25 * p
  const ratio = 0.72 - 0.1 * p
  const left = 26 + 43 * p
  const right = 16 + 53 * p
  const between = (W - left - right) / (4 * (1 + ratio))
  const within = between * ratio
  const flat = [W - right]
  for (const g of [between, within, within, between, between, within, within, between]) flat.push(flat[flat.length - 1] - g)
  const words = WORDS.map((w, wi) => {
    const first = WORDS.slice(0, wi).reduce((n, v) => n + v.types.length, 0)
    const xs = w.types.map((_, ti) => flat[first + ti])
    return { ...w, first, x: (xs[0] + xs[xs.length - 1]) / 2, xs }
  })
  return { W, H: Math.round(300 * v), v, flat, words, word: 22 + 18 * p, type: 15 + 7 * p }
}

export function Grammar() {
  const { t } = useLang()
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, amount: 0.5 })
  const [run, setRun] = useState(0)

  return (
    <section className="py-[clamp(96px,14vh,168px)]">
      <Container>
        <div className="mx-auto max-w-[860px] text-center">
          <Heading>{t({ en: 'Grammar, not guesswork.', ar: 'قواعد، لا تخمين.' })}</Heading>
          <Lede className="mx-auto mt-5">
            {t({
              en: 'Every Arabic word gets a type. The types cancel down to a single sentence, and that derivation is the translation. No model involved.',
              ar: 'تأخذ كل كلمة عربية نوعاً. تتلاشى الأنواع حتى تبقى جملة واحدة، وهذا الاشتقاق هو الترجمة نفسها. دون أي نموذج لغوي.',
            })}
          </Lede>
        </div>

        <div ref={ref} className="relative mx-auto mt-14 max-w-[980px] rounded-[var(--radius-panel)] bg-panel px-4 pb-8 pt-10 sm:px-10">
          <button
            type="button"
            onClick={() => setRun((r) => r + 1)}
            className="press absolute end-3 top-3 rounded-full p-2 text-ink-3 hover:bg-paper hover:text-ink"
            aria-label={t({ en: 'Replay', ar: 'أعد التشغيل' })}
          >
            <ArrowCounterClockwise size={18} />
          </button>
          <Derivation key={run} play={inView} />
        </div>

        <p className="mx-auto mt-6 max-w-[64ch] text-center text-[15px] leading-[1.6] text-ink-3">
          {t({
            en: 'Arabic allows verb-first and subject-first order. Both derive the same proposition, proved in Lean as vso_svo_same_meaning.',
            ar: 'تسمح العربية بتقديم الفعل أو الفاعل. كلا الترتيبين يشتق القضية نفسها، وهذا مُثبت في Lean باسم vso_svo_same_meaning.',
          })}
        </p>
      </Container>
    </section>
  )
}

function Derivation({ play }: { play: boolean }) {
  const reduce = !!useReducedMotion()
  const [ref, width] = useWidth<HTMLDivElement>()
  const { W, H, v, flat, words, word, type } = layout(width)
  const at = (s: number) => (reduce ? 0 : s)
  const go = <T extends object>(target: T) => (play ? target : {})
  const cupAt = (i: number) => at(1.5 + i * 0.5)
  const cancelledAt = (flatIndex: number) => {
    const i = CUPS.findIndex(([a, b]) => a === flatIndex || b === flatIndex)
    return i < 0 ? null : cupAt(i) + 0.35
  }
  const y0 = 134 * v

  return (
    <div ref={ref}>
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label="Pregroup derivation of ٥٩ × ٤١ يساوي ٢٤١٩">
        {words.map((w, wi) => (
          <motion.text
            key={w.text}
            x={w.x}
            y={62 * v}
            textAnchor="middle"
            className="fill-ink font-ar font-semibold"
            fontSize={word}
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={go({ opacity: 1, y: 0 })}
            transition={{ duration: 0.55, delay: at(0.1 * wi), ease: EASE }}
          >
            {w.text}
          </motion.text>
        ))}

        {words.flatMap((w, wi) =>
          w.types.map((label, ti) => {
            const f = w.first + ti
            const gone = cancelledAt(f)
            const start = at(0.7 + 0.05 * f)
            return (
              <motion.text
                key={`${wi}-${ti}`}
                x={w.xs[ti]}
                y={118 * v}
                textAnchor="middle"
                className={`font-mono ${label === 's' ? 'fill-ink font-semibold' : 'fill-ink-2'}`}
                fontSize={type}
                initial={reduce ? false : { opacity: 0 }}
                animate={go({ opacity: gone == null ? 1 : [0, 1, 1, 0.3] })}
                transition={
                  gone == null
                    ? { duration: 0.4, delay: start }
                    : { duration: gone + 0.4 - start, delay: start, times: [0, 0.12, 0.8, 1] }
                }
              >
                {label}
              </motion.text>
            )
          }),
        )}

        {CUPS.map(([a, b, h], i) => (
          <motion.path
            key={`${a}-${b}`}
            d={`M ${flat[a]} ${y0} C ${flat[a]} ${y0 + h * 1.3 * v}, ${flat[b]} ${y0 + h * 1.3 * v}, ${flat[b]} ${y0}`}
            fill="none"
            stroke="var(--color-ink-2)"
            strokeWidth="2"
            strokeLinecap="round"
            initial={reduce ? false : { pathLength: 0, opacity: 0 }}
            animate={go({ pathLength: 1, opacity: 1 })}
            transition={{ duration: 0.5, delay: cupAt(i), ease: DRAW, opacity: { duration: 0.01, delay: cupAt(i) } }}
          />
        ))}

        <motion.path
          d={`M ${flat[S]} ${y0} L ${flat[S]} ${262 * v}`}
          stroke="var(--color-ink)"
          strokeWidth="2.6"
          strokeLinecap="round"
          initial={reduce ? false : { pathLength: 0, opacity: 0 }}
          animate={go({ pathLength: 1, opacity: 1 })}
          transition={{ duration: 0.5, delay: at(3.6), ease: DRAW, opacity: { duration: 0.01, delay: at(3.6) } }}
        />
        <motion.text
          x={flat[S] + 12 + 6 * v}
          y={258 * v}
          className="fill-ink font-mono font-semibold"
          fontSize={type}
          initial={reduce ? false : { opacity: 0 }}
          animate={go({ opacity: 1 })}
          transition={{ duration: 0.4, delay: at(4.0) }}
        >
          s
        </motion.text>
      </svg>

      <motion.div
        dir="ltr"
        className="mt-2 flex flex-col items-center gap-2 text-center"
        initial={reduce ? false : { opacity: 0, y: 8, filter: 'blur(4px)' }}
        animate={go({ opacity: 1, y: 0, filter: 'blur(0px)', transitionEnd: { filter: 'none' } })}
        transition={{ duration: 0.6, delay: at(4.3), ease: EASE }}
      >
        <div className="text-[clamp(18px,2vw,24px)]">
          <Lean>{'(59:ℚ) * 41 = (2419:ℚ)'}</Lean>
        </div>
        <div className="font-mono text-[13px] text-ink-3">pregroup: n nʳ n nˡ n nʳ s nˡ n → s</div>
      </motion.div>
    </div>
  )
}
