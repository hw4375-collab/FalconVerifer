import { CaretDown, List } from '@phosphor-icons/react'
import { AnimatePresence, LayoutGroup, motion } from 'motion/react'
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { isolateMath } from '../components/ArabicText'
import { BaselineCard, LeanAvatar, VerifiedCard } from '../demo/Cards'
import { Composer } from '../demo/Composer'
import { Sidebar } from '../demo/Sidebar'
import { isArabicText, useLang, type Text } from '../i18n'
import { loadExamples, loadExampleTrace, modelLabel } from '../lib/data'
import { applyEvent, HttpError, liveAvailable, replay, runLive, traceOf, type LoopEvent, type Turn } from '../lib/stream'
import type { Example } from '../lib/types'

const STUDENTS = ['falcon-h1-arabic-3b-instruct', 'falcon-h1-7b-instruct', 'falcon-h1r-7b']
const EASE = [0.23, 1, 0.32, 1] as const

type Runner = (onEvent: (e: LoopEvent) => void, signal: AbortSignal) => Promise<void>
type Shown = Turn & { kind?: 'notice'; needsToken?: boolean }

const norm = (s: string) => s.replace(/\s+/g, ' ').trim()
let seq = 0
const newTurn = (question: string, mode: Turn['mode'], gloss?: string | null): Shown => ({
  id: `t${++seq}`,
  question,
  gloss,
  mode,
  status: 'running',
  rounds: [],
  stage: 'answering',
  stageRound: 1,
  maxRounds: 3,
})

export default function Demo() {
  const { t, lang } = useLang()
  const [turns, setTurns] = useState<Shown[]>([])
  const [examples, setExamples] = useState<Example[]>([])
  const [live, setLive] = useState<boolean | null>(null)
  const [student, setStudent] = useState(STUDENTS[0])
  const [activeKey, setActiveKey] = useState<string>()
  const [drawer, setDrawer] = useState(false)
  const ctrl = useRef<AbortController | null>(null)
  const [params] = useSearchParams()
  const running = turns.some((x) => x.status === 'running')

  useEffect(() => {
    loadExamples().then(setExamples, () => setExamples([]))
    liveAvailable().then(setLive)
    return () => ctrl.current?.abort()
  }, [])

  const update = (id: string, fn: (x: Shown) => Shown) => setTurns((ts) => ts.map((x) => (x.id === id ? fn(x) : x)))

  const start = useCallback((turn: Shown, runner: Runner) => {
    ctrl.current?.abort()
    const c = new AbortController()
    ctrl.current = c
    setTurns((ts) => [...ts, turn])
    runner((e) => update(turn.id, (x) => applyEvent(x, e) as Shown), c.signal).catch((err: Error) => {
      if (err.name === 'AbortError') update(turn.id, (x) => (x.status === 'running' ? { ...x, status: 'stopped', stage: null } : x))
      else
        update(turn.id, (x) => ({
          ...x,
          status: 'error',
          stage: null,
          error: err.message,
          needsToken: err instanceof HttpError && err.status === 401,
        }))
    })
  }, [])

  const runExample = useCallback(
    async (e: Example) => {
      setActiveKey(e.key)
      setDrawer(false)
      const trace = await loadExampleTrace(e.key)
      start(newTurn(e.question, 'replay', e.gloss), (on, sig) => replay(trace, on, sig))
    },
    [start],
  )

  const runTrace = useCallback(
    async (ref: string) => {
      let res: Response | null = null
      try {
        res = await fetch(`/api/bench/trace/${ref.split('/').map(encodeURIComponent).join('/')}`)
      } catch {
        res = null
      }
      if (!res?.ok || !(res.headers.get('content-type') ?? '').includes('json')) {
        setTurns((ts) => [
          ...ts,
          {
            ...newTurn(ref, 'replay'),
            status: 'error',
            stage: null,
            error: t({
              en: 'This recorded run is served by the NYU Falcon server (falconverifier serve).',
              ar: 'يُعرض هذا التشغيل المسجّل عبر خادم NYU Falcon ‏(falconverifier serve).',
            }),
          },
        ])
        return
      }
      const trace = traceOf(await res.json())
      start(newTurn(trace.problem, 'replay'), (on, sig) => replay(trace, on, sig))
    },
    [start, t],
  )

  const deepLinked = useRef(false)
  useEffect(() => {
    if (deepLinked.current) return
    const ex = params.get('example')
    const tr = params.get('trace')
    if (tr) {
      deepLinked.current = true
      runTrace(tr)
    } else if (ex && examples.length) {
      deepLinked.current = true
      const e = examples.find((x) => x.key === ex)
      if (e) runExample(e)
    }
  }, [params, examples, runExample, runTrace])

  // With a live server every question runs live; without one, a recorded question replays its trace.
  const ask = (text: string, expected?: string) => {
    if (!live) {
      const ex = examples.find((e) => norm(e.question) === norm(text))
      if (ex) return void runExample(ex)
      setTurns((ts) => [...ts, { ...newTurn(text, 'live'), kind: 'notice', status: 'done', stage: null }])
      return
    }
    setActiveKey(undefined)
    start(newTurn(text, 'live'), (on, sig) => runLive({ problem: text, expected, student_model: student, rounds: 3 }, on, sig))
  }

  const stop = () => ctrl.current?.abort()
  const reset = () => {
    stop()
    setTurns([])
    setActiveKey(undefined)
    setDrawer(false)
  }

  const footer =
    live === null
      ? ' '
      : live
        ? t({ en: `Live: ${modelLabel(student)} with the Lean 4 kernel.`, ar: `مباشر: ${modelLabel(student)} مع نواة Lean 4.` })
        : t({
            en: 'Recorded runs replay real traces. Live questions need the NYU Falcon server.',
            ar: 'التشغيلات المسجّلة تعيد عرض مسارات حقيقية. الأسئلة المباشرة تحتاج خادم NYU Falcon.',
          })

  return (
    <LayoutGroup>
      <main className="flex h-[calc(100dvh-4rem)] overflow-hidden">
        <aside className="hidden w-[272px] shrink-0 border-e border-rule bg-panel lg:block">
          <Sidebar examples={examples} activeKey={activeKey} onPick={runExample} onNew={reset} />
        </aside>

        <AnimatePresence>
          {drawer && (
            <>
              <motion.div
                className="fixed inset-0 top-16 z-30 bg-ink/20 lg:hidden"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setDrawer(false)}
              />
              <motion.aside
                className="fixed bottom-0 start-0 top-16 z-40 w-[288px] bg-panel lg:hidden"
                initial={{ x: lang === 'ar' ? '100%' : '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: lang === 'ar' ? '100%' : '-100%' }}
                transition={{ duration: 0.35, ease: [0.32, 0.72, 0, 1] }}
              >
                <Sidebar examples={examples} activeKey={activeKey} onPick={runExample} onNew={reset} onClose={() => setDrawer(false)} />
              </motion.aside>
            </>
          )}
        </AnimatePresence>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-14 shrink-0 items-center gap-2 px-3 sm:px-5">
            <button
              type="button"
              onClick={() => setDrawer(true)}
              className="press rounded-full p-2 hover:bg-panel lg:hidden"
              aria-label={t({ en: 'Recorded runs', ar: 'تشغيلات مسجّلة' })}
            >
              <List size={20} />
            </button>
            <ModelPicker value={student} onChange={setStudent} live={!!live} />
            <span
              className={`ms-auto items-center gap-2 whitespace-nowrap rounded-full px-3 py-1 text-[13px] text-ink-2 ${live ? 'inline-flex' : 'hidden sm:inline-flex'}`}
            >
              <span className={`size-2 rounded-full ${live ? 'bg-verified-bright' : 'bg-rule-strong'}`} />
              {live ? t({ en: 'Live', ar: 'مباشر' }) : t({ en: 'Replay only', ar: 'إعادة عرض فقط' })}
            </span>
          </div>

          {turns.length === 0 ? (
            <Empty
              examples={examples}
              onPick={runExample}
              live={!!live}
              onAsk={ask}
              composer={<ComposerSlot running={running} onSend={ask} onStop={stop} footer={footer} />}
            />
          ) : (
            <Thread turns={turns} examples={examples} onPick={runExample} onRetry={ask}>
              <ComposerSlot running={running} onSend={ask} onStop={stop} footer={footer} />
            </Thread>
          )}
        </div>
      </main>
    </LayoutGroup>
  )
}

function ComposerSlot(props: { running: boolean; onSend: (s: string) => void; onStop: () => void; footer: string }) {
  return (
    <motion.div layoutId="composer" transition={{ duration: 0.5, ease: EASE }} className="w-full">
      <Composer {...props} />
    </motion.div>
  )
}

function ModelPicker({ value, onChange, live }: { value: string; onChange: (m: string) => void; live: boolean }) {
  const { t, isAr } = useLang()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false)
    window.addEventListener('mousedown', close)
    return () => window.removeEventListener('mousedown', close)
  }, [open])
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="press flex items-center gap-1.5 whitespace-nowrap rounded-xl px-3 py-2 text-[16px] font-semibold hover:bg-panel"
      >
        {modelLabel(value)}
        <CaretDown size={14} className="text-ink-3" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.ul
            role="listbox"
            initial={{ opacity: 0, scale: 0.97, y: -4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -4 }}
            transition={{ duration: 0.16, ease: EASE }}
            style={{ transformOrigin: isAr ? 'top right' : 'top left' }}
            className="absolute start-0 top-full z-20 mt-1 w-[300px] rounded-2xl border border-rule bg-paper p-1.5 shadow-[var(--shadow-float)]"
          >
            {STUDENTS.map((m) => (
              <li key={m}>
                <button
                  type="button"
                  role="option"
                  aria-selected={m === value}
                  onClick={() => {
                    onChange(m)
                    setOpen(false)
                  }}
                  className={`w-full rounded-xl px-3 py-2.5 text-start hover:bg-panel ${m === value ? 'bg-panel' : ''}`}
                >
                  <div className="text-[15px] font-medium">{modelLabel(m)}</div>
                  <div className="text-[13px] text-ink-3">
                    {m.includes('3b')
                      ? t({ en: 'Small Arabic model, the one that needs checking', ar: 'نموذج عربي صغير، الأحوج إلى التحقق' })
                      : m.includes('h1r')
                        ? t({ en: 'Reasoning model', ar: 'نموذج استدلال' })
                        : t({ en: 'Larger general model', ar: 'نموذج عام أكبر' })}
                  </div>
                </button>
              </li>
            ))}
            {!live && (
              <li className="px-3 pb-1.5 pt-2 text-[12.5px] text-ink-3">
                {t({ en: 'Applies to live questions.', ar: 'يُطبَّق على الأسئلة المباشرة.' })}
              </li>
            )}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
}

// One-click live runs: the two stage examples from docs/PITCH.md, then two everyday-Arabic prompts for the
// deterministic dialogue fragment. Shown only when the server can run the loop.
const LIVE_PROMPTS: { title: Text; question: string; expected: string }[] = [
  {
    title: { en: 'Compound discount', ar: 'خصم مركّب' },
    question: 'يبلغ سعر هاتف 800 درهماً. خُفِّض بنسبة 10٪ ثم خُفِّض السعر الجديد بنسبة 20٪ أخرى. ما هو السعر النهائي بالدرهم؟',
    expected: '576',
  },
  {
    title: { en: 'Five friends', ar: 'خمسة أصدقاء' },
    question: 'خمسة طلاب يجلسون في الفصل، ويقول كل واحد منهم إن ثلاثة من الأربعة الباقين أصدقاؤه. هل يلزم أن أحدهم يكذب؟ أجب بنعم أو لا.',
    expected: 'نعم',
  },
  {
    title: { en: 'Restaurant bill', ar: 'فاتورة مطعم' },
    question: 'العميل: الفاتورة ٢٤٠ درهماً، تضاف ضريبة ٥٪ ورسوم خدمة ١٠٪، وتقاسمها ٣ أشخاص بالتساوي. كم يدفع كل واحد؟',
    expected: '92.4',
  },
  {
    title: { en: 'Trip day', ar: 'موعد الرحلة' },
    question: 'العميل: اليوم الخميس، والرحلة بعد ١٢ أيام. ما اليوم بعد ١٢ أيام؟',
    expected: 'الثلاثاء',
  },
]

function Empty({
  examples,
  onPick,
  live,
  onAsk,
  composer,
}: {
  examples: Example[]
  onPick: (e: Example) => void
  live: boolean
  onAsk: (q: string, expected?: string) => void
  composer: React.ReactNode
}) {
  const { t, lang } = useLang()
  return (
    <div className="flex flex-1 flex-col items-center justify-center-safe overflow-y-auto px-4 pb-10 pt-4">
      <h1 className="text-center text-[clamp(28px,3.2vw,40px)] font-semibold tracking-[-0.03em]">
        {t({ en: 'What should Falcon solve?', ar: 'ماذا تريد أن يحلّ فالكون؟' })}
      </h1>
      <div className="mt-8 w-full">{composer}</div>
      <div className="mt-8 grid w-full max-w-[860px] gap-3 sm:grid-cols-2">
        {examples.slice(0, 4).map((e, i) => (
          <motion.button
            key={e.key}
            type="button"
            onClick={() => onPick(e)}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.05 * i, ease: EASE }}
            className="press rounded-2xl border border-rule bg-paper p-4 text-start hover:border-rule-strong hover:bg-panel"
          >
            <div className="text-[14px] font-medium text-ink">{e.title[lang]}</div>
            <p lang="ar" dir="rtl" className="mt-1.5 line-clamp-2 font-ar text-[15px] leading-[1.7] text-ink-2">
              {isolateMath(e.question)}
            </p>
          </motion.button>
        ))}
      </div>
      {live && (
        <div className="mt-6 flex max-w-[860px] flex-wrap items-center justify-center gap-2 text-[14px]">
          <span className="text-ink-3">{t({ en: 'Run live:', ar: 'تشغيل مباشر:' })}</span>
          {LIVE_PROMPTS.map((p) => (
            <button
              key={p.title.en}
              type="button"
              onClick={() => onAsk(p.question, p.expected)}
              title={p.question}
              className="press rounded-full border border-rule px-3.5 py-1.5 text-ink-2 hover:border-rule-strong hover:text-ink"
            >
              {t(p.title)}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function Thread({
  turns,
  examples,
  onPick,
  onRetry,
  children,
}: {
  turns: Shown[]
  examples: Example[]
  onPick: (e: Example) => void
  onRetry: (q: string) => void
  children: React.ReactNode
}) {
  const scroller = useRef<HTMLDivElement>(null)
  const content = useRef<HTMLDivElement>(null)
  const stuck = useRef(true)

  useLayoutEffect(() => {
    const el = scroller.current
    const inner = content.current
    if (!el || !inner) return
    const onScroll = () => {
      stuck.current = el.scrollHeight - el.scrollTop - el.clientHeight < 140
    }
    const ro = new ResizeObserver(() => {
      if (stuck.current) el.scrollTo({ top: el.scrollHeight })
    })
    el.addEventListener('scroll', onScroll, { passive: true })
    ro.observe(inner)
    return () => {
      el.removeEventListener('scroll', onScroll)
      ro.disconnect()
    }
  }, [])

  useEffect(() => {
    stuck.current = true
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' })
  }, [turns.length])

  return (
    <>
      <div ref={scroller} className="flex-1 overflow-y-auto">
        <div ref={content} className="mx-auto w-full max-w-[1040px] space-y-14 px-4 pb-10 pt-6 sm:px-6">
          {turns.map((turn) => (
            <TurnView key={turn.id} turn={turn} examples={examples} onPick={onPick} onRetry={onRetry} />
          ))}
        </div>
      </div>
      <div className="shrink-0 bg-paper px-4 pb-4 pt-2 sm:px-6">{children}</div>
    </>
  )
}

function TurnView({
  turn,
  examples,
  onPick,
  onRetry,
}: {
  turn: Shown
  examples: Example[]
  onPick: (e: Example) => void
  onRetry: (q: string) => void
}) {
  const { t, isAr } = useLang()
  const ar = isArabicText(turn.question)
  return (
    <section className="space-y-5">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="flex flex-col items-end"
      >
        <div className="max-w-[min(680px,88%)] rounded-[22px] bg-panel px-5 py-3.5">
          <p dir={ar ? 'rtl' : 'ltr'} lang={ar ? 'ar' : 'en'} className={`text-[17px] leading-[1.7] ${ar ? 'font-ar' : ''}`}>
            {ar ? isolateMath(turn.question) : turn.question}
          </p>
        </div>
        {turn.gloss && !isAr && <p className="mt-1.5 max-w-[min(680px,88%)] text-end text-[13px] text-ink-3">{turn.gloss}</p>}
      </motion.div>

      {turn.kind === 'notice' ? (
        <Notice examples={examples} onPick={onPick} />
      ) : (
        <div className="grid items-start gap-4 md:grid-cols-2">
          <BaselineCard turn={turn} />
          <VerifiedCard turn={turn} />
        </div>
      )}
      {turn.needsToken && <TokenForm onSave={() => onRetry(turn.question)} />}
      {turn.status === 'error' && !turn.needsToken && turn.kind !== 'notice' && (
        <p className="text-[14px] text-ink-3">{t({ en: 'The run failed before finishing.', ar: 'توقّف التشغيل قبل اكتماله.' })}</p>
      )}
    </section>
  )
}

function Notice({ examples, onPick }: { examples: Example[]; onPick: (e: Example) => void }) {
  const { t, lang } = useLang()
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: EASE }}
      className="flex gap-3"
    >
      <LeanAvatar />
      <div className="min-w-0 flex-1 rounded-[20px] border border-rule bg-paper p-5">
        <p className="text-[16px] leading-[1.6]">
          {t({
            en: 'Live verification is not connected here. It needs the NYU Falcon server with Lean 4 and a Falcon API key. These recorded runs replay real traces:',
            ar: 'التحقق المباشر غير متصل هنا؛ يحتاج خادم NYU Falcon مع Lean 4 ومفتاح Falcon. هذه تشغيلات مسجّلة تعيد عرض مسارات حقيقية:',
          })}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {examples.map((e) => (
            <button
              key={e.key}
              type="button"
              onClick={() => onPick(e)}
              className="press rounded-full border border-rule px-3.5 py-1.5 text-[14px] hover:border-ink hover:bg-panel"
            >
              {e.title[lang]}
            </button>
          ))}
        </div>
      </div>
    </motion.div>
  )
}

function TokenForm({ onSave }: { onSave: () => void }) {
  const { t } = useLang()
  const [value, setValue] = useState('')
  return (
    <form
      className="flex flex-wrap items-center gap-2 rounded-2xl border border-rule p-3"
      onSubmit={(e) => {
        e.preventDefault()
        try {
          window.localStorage.setItem('fv-token', value.trim())
        } catch {
          // storage unavailable
        }
        onSave()
      }}
    >
      <label htmlFor="fv-token" className="text-[14px] text-ink-2">
        {t({ en: 'This server needs an access token', ar: 'يتطلب هذا الخادم رمز وصول' })}
      </label>
      <input
        id="fv-token"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="min-w-[200px] flex-1 rounded-xl border border-rule-strong bg-paper px-3 py-2 text-[15px] outline-none focus:border-ink"
      />
      <button type="submit" className="press rounded-full bg-ink px-4 py-2 text-[14px] font-medium text-paper">
        {t({ en: 'Save and retry', ar: 'حفظ وإعادة المحاولة' })}
      </button>
    </form>
  )
}
