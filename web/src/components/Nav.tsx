import { GithubLogo } from '@phosphor-icons/react'
import { motion, useMotionValueEvent, useScroll } from 'motion/react'
import { useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { useLang } from '../i18n'
import { PRODUCT, Wordmark } from './Mark'

export const REPO_URL = 'https://github.com/hw4375-collab/FalconVerifer'

const LINKS = [
  { to: '/', label: { en: 'Story', ar: 'القصة' } },
  { to: '/demo', label: { en: 'Demo', ar: 'التجربة' } },
  { to: '/results', label: { en: 'Results', ar: 'النتائج' } },
]

export function Nav() {
  const { t, lang, setLang } = useLang()
  const { pathname } = useLocation()
  const { scrollY } = useScroll()
  const [scrolled, setScrolled] = useState(false)
  useMotionValueEvent(scrollY, 'change', (y) => setScrolled(y > 8))

  return (
    <header
      className={`sticky top-[env(safe-area-inset-top,0px)] z-40 h-16 border-b bg-paper/95 transition-colors duration-300 ${
        scrolled || pathname !== '/' ? 'border-rule' : 'border-transparent'
      }`}
    >
      <div className="mx-auto flex h-full max-w-[1320px] items-center justify-between px-5 md:px-8">
        <Link to="/" className="press text-[17px] text-ink" aria-label={PRODUCT}>
          <Wordmark collapse />
        </Link>

        <nav className="flex items-center gap-0.5 sm:gap-2">
          {LINKS.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end
              className={({ isActive }) =>
                `press relative rounded-full px-2.5 py-1.5 text-[15px] sm:px-3 ${isActive ? 'text-ink' : 'text-ink-2 hover:text-ink'}`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.span
                      layoutId="nav-active"
                      className="absolute inset-0 -z-10 rounded-full bg-panel"
                      transition={{ type: 'spring', duration: 0.45, bounce: 0.15 }}
                    />
                  )}
                  {t(l.label)}
                </>
              )}
            </NavLink>
          ))}
          <span className="mx-1 hidden h-5 w-px bg-rule sm:block" />
          <button
            type="button"
            onClick={() => setLang(lang === 'en' ? 'ar' : 'en')}
            className="press rounded-full px-2.5 py-1.5 text-[15px] text-ink-2 hover:text-ink sm:px-3"
            lang={lang === 'en' ? 'ar' : 'en'}
          >
            {lang === 'en' ? 'العربية' : 'English'}
          </button>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noreferrer"
            className="press hidden rounded-full p-2 text-ink-2 hover:text-ink sm:block"
            aria-label="GitHub"
          >
            <GithubLogo size={20} weight="regular" />
          </a>
        </nav>
      </div>
    </header>
  )
}
