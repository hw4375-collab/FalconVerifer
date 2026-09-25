import { useLang } from '../i18n'
import { REPO_URL } from './Nav'
import { BASE } from '../lib/data'
import { ORG, ORG_URL } from './Mark'

export function Footer() {
  const { t } = useLang()
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto flex max-w-[1320px] flex-col gap-6 px-5 py-10 text-[14px] text-ink-2 md:flex-row md:items-center md:justify-between md:px-8">
        <a href={ORG_URL} target="_blank" rel="noreferrer" className="press flex items-center gap-3 text-ink">
          <img src={`${BASE}brand/chaosbutterfly-logo.png`} alt={ORG} className="h-10 w-auto" />
          <span className="flex flex-col leading-tight">
            <span className="font-medium">{t({ en: `Built by ${ORG}`, ar: `من تطوير ${ORG}` })}</span>
            <span className="text-[13px] text-ink-2">
              {t({ en: 'Formal assurance for Arabic AI', ar: 'ضمان صوري للذكاء الاصطناعي العربي' })}
            </span>
          </span>
        </a>
        <p className="max-w-[60ch]">
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
