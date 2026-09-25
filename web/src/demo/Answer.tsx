import { isolateMath } from '../components/ArabicText'
import { Lean } from '../components/Lean'
import { isArabicText } from '../i18n'
import { cleanAnswer } from '../lib/stream'

// `code` spans (Lean propositions quoted in Lean's feedback) render as left-to-right Lean;
// the surrounding Arabic keeps its equations isolated so bidi does not reverse them.
function withCode(text: string, ar: boolean) {
  return text.split(/`([^`]+)`/g).map((part, i) =>
    i % 2 ? (
      <bdi key={i} dir="ltr">
        <Lean className="text-[0.93em]">{part}</Lean>
      </bdi>
    ) : ar ? (
      <span key={i}>{isolateMath(part)}</span>
    ) : (
      part
    ),
  )
}

export function RichText({ text, className = '' }: { text: string; className?: string }) {
  const ar = isArabicText(text)
  return (
    <div dir={ar ? 'rtl' : 'ltr'} lang={ar ? 'ar' : 'en'} className={`whitespace-pre-line ${ar ? 'font-ar' : ''} ${className}`}>
      {withCode(text, ar)}
    </div>
  )
}

export function Reasoning({ raw }: { raw: string }) {
  return <RichText text={cleanAnswer(raw)} className="text-[15px] leading-[1.75] text-ink-2" />
}

export function FinalAnswer({ value, tone = 'ink' }: { value: string | null; tone?: 'ink' | 'refuted' | 'verified' | 'muted' }) {
  if (!value) return <span className="text-[18px] text-ink-3">—</span>
  const ar = isArabicText(value)
  const size = value.length > 26 ? 'text-[20px] leading-[1.5]' : value.length > 12 ? 'text-[26px] leading-[1.3]' : 'text-[34px] leading-[1.15]'
  const color = { ink: 'text-ink', refuted: 'text-refuted', verified: 'text-verified', muted: 'text-ink-3' }[tone]
  return (
    <div dir={ar ? 'rtl' : 'ltr'} lang={ar ? 'ar' : 'en'} className={`font-semibold tracking-[-0.02em] ${size} ${color} ${ar ? 'font-ar' : ''}`}>
      {ar ? isolateMath(value) : value}
    </div>
  )
}
