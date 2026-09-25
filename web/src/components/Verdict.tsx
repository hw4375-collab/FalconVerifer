import { Check, GlobeSimple, Minus, Question, X } from '@phosphor-icons/react'
import type { Text } from '../i18n'
import { useLang } from '../i18n'
import type { Verdict as V } from '../lib/types'

export const VERDICT_LABEL: Record<V, Text> = {
  verified: { en: 'proved', ar: 'مُثبَت' },
  refuted: { en: 'refuted', ar: 'مدحوض' },
  unknown: { en: 'undecided', ar: 'غير محسوم' },
  ill_formed: { en: 'ill-formed', ar: 'صياغة معيبة' },
  unverified_premise: { en: 'unchecked premise', ar: 'مقدّمة غير مُتحقَّق منها' },
  skipped: { en: 'no claim', ar: 'بلا ادعاء' },
}

const TONE: Record<V, string> = {
  verified: 'text-verified bg-verified-wash',
  refuted: 'text-refuted bg-refuted-wash',
  unknown: 'text-unknown bg-unknown-wash',
  ill_formed: 'text-unknown bg-unknown-wash',
  unverified_premise: 'text-ink-2 outline-1 -outline-offset-1 outline-dashed outline-rule-strong',
  skipped: 'text-ink-3 bg-panel',
}

export function VerdictIcon({ verdict, size = 14 }: { verdict: V; size?: number }) {
  const weight = 'bold' as const
  if (verdict === 'verified') return <Check size={size} weight={weight} />
  if (verdict === 'refuted') return <X size={size} weight={weight} />
  if (verdict === 'skipped') return <Minus size={size} weight={weight} />
  if (verdict === 'unverified_premise') return <GlobeSimple size={size} weight={weight} />
  return <Question size={size} weight={weight} />
}

export function VerdictBadge({ verdict, label, className = '' }: { verdict: V; label?: string; className?: string }) {
  const { t } = useLang()
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[13px] font-medium leading-5 ${TONE[verdict]} ${className}`}
    >
      <VerdictIcon verdict={verdict} size={13} />
      {label ?? t(VERDICT_LABEL[verdict])}
    </span>
  )
}
