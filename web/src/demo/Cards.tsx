import { ArrowBendUpLeft, CaretDown, CaretRight } from '@phosphor-icons/react'
import { AnimatePresence, motion } from 'motion/react'
import { useState, type ReactNode } from 'react'
import { Lean } from '../components/Lean'
import { Turnstile } from '../components/Mark'
import { VERDICT_LABEL, VerdictBadge, VerdictIcon } from '../components/Verdict'
import { useLang, type Text } from '../i18n'
import { modelLabel } from '../lib/data'
import type { Turn } from '../lib/stream'
import type { Round, Verdict } from '../lib/types'
import { FinalAnswer, Reasoning, RichText } from './Answer'

const EASE = [0.23, 1, 0.32, 1] as const

function Card({ children, emphasis = false }: { children: ReactNode; emphasis?: boolean }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: EASE }}
      className={`flex min-w-0 flex-col rounded-[20px] border bg-paper p-5 sm:p-6 ${emphasis ? 'border-ink/30' : 'border-rule'}`}
    >
      {children}
    </motion.article>
  )
}

function Header({ icon, title, tag }: { icon: ReactNode; title: string; tag?: ReactNode }) {
  return (
    <header className="flex items-center gap-3">
      {icon}
      <div className="min-w-0 flex-1">
        <div className="truncate text-[15px] font-semibold">{title}</div>
      </div>
      {tag}
    </header>
  )
}

export const FalconAvatar = () => (
  <span className="flex size-8 shrink-0 items-center justify-center rounded-full border border-rule-strong font-ar text-[16px] font-semibold">
    ف
  </span>
)

export const LeanAvatar = () => (
  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-ink text-paper">
    <Turnstile className="size-[15px]" />
  </span>
)

function Thinking({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 py-2 text-[15px] text-ink-2">
      <span className="relative flex size-2.5">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-ink/40" />
        <span className="relative inline-flex size-2.5 rounded-full bg-ink" />
      </span>
      {label}
    </div>
  )
}

function Disclosure({ label, children, defaultOpen = false }: { label: Text; children: ReactNode; defaultOpen?: boolean }) {
  const { t } = useLang()
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="mt-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="press inline-flex items-center gap-1.5 rounded-full py-1 text-[14px] font-medium text-ink-2 hover:text-ink"
      >
        {t(label)}
        <CaretDown size={14} className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="overflow-hidden"
          >
            <div className="pt-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const QUEUED: Text = { en: 'Queued for a free Lean worker', ar: 'في انتظار عامل Lean متاح' }

const STAGE_LABEL: Record<string, Text> = {
  answering: { en: 'Falcon is answering', ar: 'فالكون يجيب' },
  formalizing: { en: 'Translating each step to Lean 4', ar: 'ترجمة كل خطوة إلى Lean 4' },
  checking: { en: 'The Lean kernel is checking', ar: 'نواة Lean تتحقق' },
  teaching: { en: 'Sending the correction to Falcon', ar: 'إرسال التصحيح إلى فالكون' },
}

// ---------------------------------------------------------------- Falcon alone

export function BaselineCard({ turn }: { turn: Turn }) {
  const { t } = useLang()
  const r1 = turn.rounds[0]
  const answered = !!r1?.answer.raw
  const report = r1?.report
  const verdict = report?.final
  const tone = verdict === 'refuted' ? 'refuted' : verdict === 'verified' ? 'verified' : 'ink'

  return (
    <Card>
      <Header
        icon={<FalconAvatar />}
        title={turn.student ? modelLabel(turn.student) : 'Falcon'}
        tag={<span className="text-[13px] text-ink-3">{t({ en: 'answer as given', ar: 'الإجابة كما هي' })}</span>}
      />
      <div className="mt-4 flex-1">
        {!answered && turn.status === 'running' && <Thinking label={t(STAGE_LABEL.answering)} />}
        {answered && (
          <>
            <FinalAnswer value={r1.answer.final} tone={tone} />
            {!r1.answer.final && (
              <p className="mt-1 text-[14px] text-ink-3">{t({ en: 'No final answer line', ar: 'لا يوجد سطر «الجواب النهائي»' })}</p>
            )}
            <Disclosure label={{ en: 'Falcon’s reasoning', ar: 'استدلال فالكون' }}>
              <Reasoning raw={r1.answer.raw} />
            </Disclosure>
          </>
        )}
      </div>
      {answered && (
        <div className="mt-5 border-t border-rule pt-4">
          {!report ? (
            <Thinking label={t({ en: 'Lean is checking this answer', ar: 'Lean يتحقق من هذه الإجابة' })} />
          ) : (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[14px]">
              <span className="text-ink-3">{t({ en: 'Lean 4 on this answer', ar: 'حكم Lean 4 على هذه الإجابة' })}</span>
              <VerdictBadge verdict={verdict!} />
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

// ---------------------------------------------------------------- Falcon + Lean

type Chip = { key: string; label: Text; state: 'done' | 'active' | 'todo'; tone?: Verdict | 'teach' }

function chipsOf(turn: Turn): Chip[] {
  const chips: Chip[] = []
  const n = Math.max(turn.rounds.length, turn.stageRound)
  for (let r = 1; r <= n; r++) {
    const round = turn.rounds[r - 1]
    const here = turn.stageRound === r
    chips.push({
      key: `f${r}`,
      label: { en: `Falcon, round ${r}`, ar: `فالكون، الجولة ${r}` },
      state: round?.answer.raw ? 'done' : here && turn.stage === 'answering' ? 'active' : 'todo',
    })
    if (round?.answer.raw || (here && (turn.stage === 'formalizing' || turn.stage === 'checking'))) {
      chips.push({
        key: `l${r}`,
        label: { en: 'Lean 4', ar: 'Lean 4' },
        state: round?.report ? 'done' : 'active',
        tone: round?.report?.final,
      })
    }
    if (round?.feedback || (here && turn.stage === 'teaching')) {
      chips.push({ key: `c${r}`, label: { en: 'correction', ar: 'تصحيح' }, state: round?.feedback ? 'done' : 'active', tone: 'teach' })
    }
  }
  return chips
}

const CHIP_TONE: Record<string, string> = {
  verified: 'border-verified/30 bg-verified-wash text-verified',
  refuted: 'border-refuted/30 bg-refuted-wash text-refuted',
  unknown: 'border-unknown/30 bg-unknown-wash text-unknown',
  ill_formed: 'border-unknown/30 bg-unknown-wash text-unknown',
  unverified_premise: 'border-dashed border-rule-strong bg-paper text-ink-2',
  skipped: 'border-rule bg-panel text-ink-2',
  teach: 'border-refuted/25 bg-paper text-refuted',
}

export function PipelineStrip({ turn }: { turn: Turn }) {
  const { t } = useLang()
  const chips = chipsOf(turn)
  return (
    <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-2" aria-label={t({ en: 'Verification loop', ar: 'حلقة التحقق' })}>
      <AnimatePresence initial={false}>
        {chips.map((c, i) => (
          <motion.li
            key={c.key}
            layout
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="flex items-center gap-1.5"
          >
            {i > 0 && <CaretRight size={12} weight="bold" className="text-ink-3 rtl:rotate-180" aria-hidden />}
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[13px] font-medium ${
                c.state === 'active'
                  ? 'border-ink bg-ink text-paper'
                  : c.state === 'done' && c.tone
                    ? CHIP_TONE[c.tone]
                    : 'border-rule bg-panel text-ink-2'
              }`}
            >
              {c.state === 'active' && <span className="size-1.5 animate-pulse rounded-full bg-paper" />}
              {c.state === 'done' && c.tone && c.tone !== 'teach' && <VerdictIcon verdict={c.tone} size={12} />}
              {t(c.label)}
            </span>
          </motion.li>
        ))}
      </AnimatePresence>
    </ol>
  )
}

function summary(turn: Turn, t: (x: Text) => string): string {
  const tr = turn.trace!
  const n = tr.rounds.length
  const hits = tr.rounds.reduce((k, r) => k + (r.report?.cacheHits ?? 0), 0)
  const s = `${Math.round(tr.latency)} s` + (hits ? t({ en: ` · ${hits} from memory`, ar: ` · ${hits} من الذاكرة` }) : '')
  if (tr.status === 'verified' && n > 1)
    return t({ en: `Refuted in round 1, proved in round ${n}. ${s}.`, ar: `دُحضت في الجولة 1 وأُثبتت في الجولة ${n}. ${s}.` })
  if (tr.status === 'verified') return t({ en: `Proved in round 1. ${s}.`, ar: `أُثبتت في الجولة الأولى. ${s}.` })
  if (tr.status === 'max_rounds')
    return t({ en: `Still refuted after ${n} rounds. ${s}.`, ar: `ما زالت مدحوضة بعد ${n} جولات. ${s}.` })
  return t({ en: `Lean could not decide the final answer. ${s}.`, ar: `لم يتمكن Lean من الحكم على الجواب النهائي. ${s}.` })
}

export function VerifiedCard({ turn }: { turn: Turn }) {
  const { t } = useLang()
  const tr = turn.trace
  const status = tr?.status
  const verdict: Verdict | undefined =
    status === 'verified' ? 'verified' : status === 'refuted' || status === 'max_rounds' ? 'refuted' : status ? 'unknown' : undefined
  const tag =
    turn.mode === 'replay' ? (
      <span className="rounded-full bg-panel px-2 py-0.5 text-[12px] font-medium text-ink-2">{t({ en: 'recorded run', ar: 'تشغيل مسجّل' })}</span>
    ) : (
      <span className="rounded-full bg-verified-wash px-2 py-0.5 text-[12px] font-medium text-verified">{t({ en: 'live', ar: 'مباشر' })}</span>
    )

  return (
    <Card emphasis>
      <Header icon={<LeanAvatar />} title={t({ en: 'Falcon + Lean 4', ar: 'فالكون + Lean 4' })} tag={tag} />
      <div className="mt-4">
        <PipelineStrip turn={turn} />
      </div>
      <div className="mt-5 flex-1">
        {turn.status === 'running' && turn.stage && <Thinking label={t(STAGE_LABEL[turn.stage])} />}
        {turn.status === 'running' && !turn.stage && turn.rounds.length === 0 && (
          <Thinking label={t(turn.note?.startsWith('queued') ? QUEUED : STAGE_LABEL.answering)} />
        )}
        {tr && (
          <motion.div initial={{ opacity: 0, filter: 'blur(4px)' }} animate={{ opacity: 1, filter: 'blur(0px)', transitionEnd: { filter: 'none' } }} transition={{ duration: 0.5, ease: EASE }}>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <FinalAnswer value={tr.final} tone={verdict === 'verified' ? 'verified' : verdict === 'refuted' ? 'refuted' : 'ink'} />
              {verdict && <VerdictBadge verdict={verdict} />}
            </div>
            <p className="mt-2 text-[14px] text-ink-2">{summary(turn, t)}</p>
            {turn.memory && turn.memory.seenBefore > 0 && <MemoryNote memory={turn.memory} />}
            <Disclosure label={{ en: 'Show the proof', ar: 'اعرض البرهان' }}>
              <ProofPanel rounds={tr.rounds} />
            </Disclosure>
          </motion.div>
        )}
        {turn.status === 'error' && <p className="text-[15px] text-refuted">{turn.error}</p>}
        {turn.status === 'stopped' && <p className="text-[15px] text-ink-3">{t({ en: 'Stopped.', ar: 'تم الإيقاف.' })}</p>}
      </div>
    </Card>
  )
}

function MemoryNote({ memory }: { memory: NonNullable<Turn['memory']> }) {
  const { t } = useLang()
  const last = memory.lastStatus in VERDICT_LABEL ? t(VERDICT_LABEL[memory.lastStatus as Verdict]) : memory.lastStatus
  const recalled = memory.expectedRecalled ? t({ en: ', expected answer recalled', ar: '، واستُرجع الجواب المتوقع' }) : ''
  return (
    <p className="mt-1 text-[13px] leading-[1.5] text-ink-3">
      {t({
        en: `Seen ${memory.seenBefore}× before${last ? ` (last: ${last}${recalled})` : ''}. Falcon still answered afresh; only kernel verdicts and checked translations are reused, each marked in the proof.`,
        ar: `ورد هذا السؤال ${memory.seenBefore} مرة من قبل${last ? ` (آخر نتيجة: ${last}${recalled})` : ''}. أجاب فالكون من جديد؛ لا يُعاد استخدام إلا أحكام النواة والترجمات المُتحقَّق منها، وكلٌّ منها معلَّم في البرهان.`,
      })}
    </p>
  )
}

// ---------------------------------------------------------------- proof details

export function ProofPanel({ rounds }: { rounds: Round[] }) {
  const { t } = useLang()
  return (
    <ol className="space-y-5">
      {rounds.map((r) => {
        const rep = r.report
        const claims = rep?.steps.filter((s) => s.verdict !== 'skipped') ?? []
        const grammar = r.formalization?.problemNote?.startsWith('pregroup:') ? r.formalization.problemNote : null
        return (
          <li key={r.round} className="border-t border-rule pt-5 first:border-t-0 first:pt-0">
            <div className="flex items-center justify-between gap-3">
              <span className="text-[14px] font-semibold">{t({ en: `Round ${r.round}`, ar: `الجولة ${r.round}` })}</span>
              {rep && <VerdictBadge verdict={rep.final} />}
            </div>
            <ul className="mt-3 space-y-3">
              {claims.map((s) => (
                <li key={s.index} className="grid gap-1.5">
                  <RichText text={s.text} className="line-clamp-2 text-[14px] leading-[1.6] text-ink-2" />
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="min-w-0 text-[13px]">{s.leanProp && <Lean>{s.leanProp}</Lean>}</div>
                    <span className="inline-flex items-center gap-2">
                      {s.cached && <span className="text-[12px] text-ink-3">{t({ en: 'from memory', ar: 'من الذاكرة' })}</span>}
                      <VerdictBadge verdict={s.verdict} />
                    </span>
                  </div>
                </li>
              ))}
              <li className="grid gap-1.5 border-t border-rule pt-3">
                <div className="flex flex-wrap items-baseline gap-2 text-[14px] text-ink-2">
                  <span>{t({ en: 'Final answer', ar: 'الجواب النهائي' })}</span>
                  <RichText text={r.answer.final ?? '—'} className="font-semibold text-ink" />
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0 text-[13px]">
                    {r.formalization?.problemProp && <Lean>{r.formalization.problemProp}</Lean>}
                  </div>
                  {rep && <VerdictBadge verdict={rep.final} />}
                </div>
                {grammar && (
                  <div dir="auto" className="font-mono text-[12px] leading-[1.6] text-ink-3 [overflow-wrap:anywhere]">
                    {grammar}
                  </div>
                )}
              </li>
            </ul>
            {r.feedback && (
              <div className="mt-4">
                <div className="flex items-center gap-2 text-[13px] font-medium text-refuted">
                  <ArrowBendUpLeft size={15} weight="bold" className="rtl:-scale-x-100" aria-hidden />
                  {t({ en: 'Correction sent to Falcon', ar: 'التصحيح المُرسَل إلى فالكون' })}
                </div>
                <RichText text={r.feedback} className="mt-1.5 ps-[23px] text-[14px] leading-[1.7] text-ink" />
              </div>
            )}
            {rep?.lean && (
              <details className="mt-3">
                <summary className="cursor-pointer text-[13px] text-ink-3 hover:text-ink">
                  {t({ en: 'Lean source sent to the kernel', ar: 'شيفرة Lean المرسلة إلى النواة' })}
                </summary>
                <pre dir="ltr" className="mt-2 overflow-x-auto rounded-lg bg-panel p-3 font-mono text-[12px] leading-[1.7] text-ink-2">
                  {rep.lean}
                </pre>
              </details>
            )}
          </li>
        )
      })}
    </ol>
  )
}
