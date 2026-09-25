import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type Lang = 'en' | 'ar'
export type Text = { en: string; ar: string }

type LangState = {
  lang: Lang
  dir: 'ltr' | 'rtl'
  isAr: boolean
  setLang: (lang: Lang) => void
  t: (text: Text) => string
}

const LangContext = createContext<LangState | null>(null)

function initialLang(): Lang {
  const fromUrl = new URLSearchParams(window.location.search).get('lang')
  if (fromUrl === 'ar' || fromUrl === 'en') return fromUrl
  try {
    const stored = window.localStorage.getItem('fv-lang')
    if (stored === 'ar' || stored === 'en') return stored
  } catch {
    // storage unavailable (private mode, blocked site data)
  }
  return 'en'
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)

  useEffect(() => {
    const root = document.documentElement
    root.lang = lang
    root.dir = lang === 'ar' ? 'rtl' : 'ltr'
  }, [lang])

  const setLang = useCallback((next: Lang) => {
    setLangState(next)
    try {
      window.localStorage.setItem('fv-lang', next)
    } catch {
      // ignore
    }
  }, [])

  const value = useMemo<LangState>(
    () => ({
      lang,
      dir: lang === 'ar' ? 'rtl' : 'ltr',
      isAr: lang === 'ar',
      setLang,
      t: (text) => text[lang],
    }),
    [lang, setLang],
  )

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>
}

export function useLang(): LangState {
  const ctx = useContext(LangContext)
  if (!ctx) throw new Error('useLang outside LangProvider')
  return ctx
}

export const isArabicText = (s: string | null | undefined) =>
  !!s && /[؀-ۿ]/.test(s) && (s.match(/[؀-ۿ]/g)?.length ?? 0) > s.length * 0.2
