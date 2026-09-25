import { useLang } from '../i18n'
import { REPO_URL } from './Nav'
import { BASE } from '../lib/data'

export function Footer() {
  const { t } = useLang()
  return (
    <footer className="border-t border-rule">
      <div className="mx-auto flex max-w-[1320px] flex-col gap-6 px-5 py-10 text-[14px] text-ink-2 md:flex-row md:items-center md:justify-between md:px-8">
        <div className="flex items-center gap-3">
          <img src={`${BASE}brand/chaosbutterfly-mark.png`} alt="" className="h-7 w-auto" />
          <span>{t({ en: 'Built by ChaosButterfly', ar: 'من تطوير ChaosButterfly' })}</span>
        </div>
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
