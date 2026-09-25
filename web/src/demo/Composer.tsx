import { ArrowUp, Stop } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { useLang } from '../i18n'

export function Composer({
  running,
  onSend,
  onStop,
  footer,
}: {
  running: boolean
  onSend: (text: string) => void
  onStop: () => void
  footer?: React.ReactNode
}) {
  const { t } = useLang()
  const [value, setValue] = useState('')
  const box = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = box.current
    if (!el) return
    el.style.height = '0px'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }, [value])

  const send = () => {
    const text = value.trim()
    if (!text || running) return
    onSend(text)
    setValue('')
  }

  return (
    <div className="mx-auto w-full max-w-[860px]">
      <div className="flex items-end gap-2 rounded-[26px] border border-rule-strong bg-paper p-2 ps-5 transition-colors focus-within:border-ink">
        <label className="sr-only" htmlFor="fv-question">
          {t({ en: 'Your question', ar: 'سؤالك' })}
        </label>
        <textarea
          id="fv-question"
          ref={box}
          rows={1}
          dir="auto"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault()
              send()
            }
          }}
          placeholder={t({
            en: 'Ask a math or logic question, in Arabic or English',
            ar: 'اكتب سؤالاً في الرياضيات أو المنطق، بالعربية أو الإنجليزية',
          })}
          className="max-h-[180px] min-h-[44px] flex-1 resize-none bg-transparent py-2.5 text-[16px] leading-[1.6] text-ink outline-none placeholder:text-ink-3 focus-visible:outline-none"
        />
        {running ? (
          <button
            type="button"
            onClick={onStop}
            className="press flex size-11 shrink-0 items-center justify-center rounded-full bg-ink text-paper"
            aria-label={t({ en: 'Stop', ar: 'إيقاف' })}
          >
            <Stop size={16} weight="fill" />
          </button>
        ) : (
          <button
            type="button"
            onClick={send}
            disabled={!value.trim()}
            className="press flex size-11 shrink-0 items-center justify-center rounded-full bg-ink text-paper disabled:bg-rule disabled:text-ink-3"
            aria-label={t({ en: 'Send', ar: 'إرسال' })}
          >
            <ArrowUp size={18} weight="bold" />
          </button>
        )}
      </div>
      {footer && <div className="mt-2 px-4 text-center text-[13px] text-ink-3">{footer}</div>}
    </div>
  )
}
