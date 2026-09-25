import { BASE } from '../lib/data'

export function Turnstile({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className={className} fill="none">
      <path d="M6 4v16M6 12h13" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  )
}

export const PRODUCT = 'NYU Falcon'
export const ORG = 'ChaosButterfly.ai'
export const ORG_URL = 'https://chaosbutterfly.ai'

export function Wordmark({ className = '', collapse = false }: { className?: string; collapse?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-2.5 font-semibold tracking-[-0.02em] ${className}`} dir="ltr">
      <img src={`${BASE}brand/chaosbutterfly-mark.png`} alt="" className="h-[1.55em] w-auto" />
      <span className={collapse ? 'max-sm:hidden' : ''}>
        {PRODUCT}
        <span className="ml-2 font-normal text-ink-2 max-md:hidden">
          by <span className="font-medium text-ink">{ORG}</span>
        </span>
      </span>
    </span>
  )
}
