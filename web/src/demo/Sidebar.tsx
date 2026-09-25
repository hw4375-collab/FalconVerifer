import { NotePencil, X } from '@phosphor-icons/react'
import { useLang } from '../i18n'
import type { Example } from '../lib/types'

export function Sidebar({
  examples,
  activeKey,
  onPick,
  onNew,
  onClose,
}: {
  examples: Example[]
  activeKey?: string
  onPick: (e: Example) => void
  onNew: () => void
  onClose?: () => void
}) {
  const { t, lang } = useLang()
  const groups: { title: string; items: Example[] }[] = [
    { title: t({ en: 'Arithmetic', ar: 'حساب' }), items: examples.filter((e) => e.kind === 'arith') },
    { title: t({ en: 'Logic', ar: 'منطق' }), items: examples.filter((e) => e.kind === 'logic') },
  ]
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 p-3">
        <button
          type="button"
          onClick={onNew}
          className="press flex flex-1 items-center gap-2 rounded-xl px-3 py-2.5 text-[15px] font-medium hover:bg-rule/60"
        >
          <NotePencil size={18} />
          {t({ en: 'New chat', ar: 'محادثة جديدة' })}
        </button>
        {onClose && (
          <button type="button" onClick={onClose} className="press rounded-full p-2 hover:bg-rule/60" aria-label={t({ en: 'Close', ar: 'إغلاق' })}>
            <X size={18} />
          </button>
        )}
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-6">
        <div className="px-3 pb-1 pt-3 text-[13px] font-medium text-ink-3">{t({ en: 'Recorded runs', ar: 'تشغيلات مسجّلة' })}</div>
        {groups.map((g) => (
          <div key={g.title} className="mt-3">
            <div className="px-3 pb-1 text-[12px] text-ink-3">{g.title}</div>
            <ul>
              {g.items.map((e) => (
                <li key={e.key}>
                  <button
                    type="button"
                    onClick={() => onPick(e)}
                    className={`press flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-start text-[14.5px] ${
                      activeKey === e.key ? 'bg-rule/70 text-ink' : 'text-ink-2 hover:bg-rule/50 hover:text-ink'
                    }`}
                  >
                    <span className="truncate">{e.title[lang]}</span>
                    <span className="flex shrink-0 items-center gap-1" aria-hidden>
                      {e.rounds > 1 && <span className="size-1.5 rounded-full bg-refuted-bright" />}
                      <span className="size-1.5 rounded-full bg-verified-bright" />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
