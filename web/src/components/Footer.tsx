import { useLang } from '../i18n'
import { REPO_URL } from './Nav'
import { BASE } from '../lib/data'
import { ORG, ORG_URL } from './Mark'

export function Footer() {
  const { t } = useLang()
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto flex max-w-[1320px] flex-col items-center gap-6 px-5 py-12 text-center md:flex-row md:justify-between md:px-8 md:text-start">
        <a href={ORG_URL} target="_blank" rel="noreferrer" className="press flex flex-col items-center gap-4 text-ink md:flex-row md:gap-5">
          <img src={`${BASE}brand/chaosbutterfly-logo.png`} alt={ORG} className="h-16 w-auto md:h-20" />
          <span className="flex flex-col leading-tight">
            <span className="text-[13px] uppercase tracking-[0.14em] text-ink-2">
              {t({ en: 'Built by', ar: 'من تطوير' })}
            </span>
            <span className="text-[24px] font-semibold tracking-[-0.02em]">{ORG}</span>
            <span className="mt-1 text-[15px] text-ink-2">
              {t({ en: 'The trust layer for Arabic AI', ar: 'طبقة الثقة للذكاء الاصطناعي العربي' })}
            </span>
          </span>
        </a>
        <a
          href={ORG_URL}
          target="_blank"
          rel="noreferrer"
          className="press rounded-full border border-ink px-5 py-2.5 text-[15px] font-medium text-ink hover:bg-ink hover:text-paper"
        >
          chaosbutterfly.ai ↗
        </a>
      </div>
      <div className="mx-auto max-w-[1320px] border-t border-rule px-5 py-5 text-[13px] text-ink-2 md:px-8">
        <p className="max-w-[80ch]">
          {t({
            en: 'Falcon models are developed by TII. NYU Falcon is an independent project.',
            ar: 'نماذج Falcon من تطوير معهد الابتكار التكنولوجي. NYU Falcon مشروع مستقل.',
          })}{' '}
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="text-ink underline">
            GitHub
          </a>
        </p>
      </div>
    </footer>
  )
}
