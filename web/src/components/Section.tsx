import type { ReactNode } from 'react'

export const Container = ({ children, className = '' }: { children: ReactNode; className?: string }) => (
  <div className={`mx-auto w-full max-w-[1320px] px-5 md:px-8 ${className}`}>{children}</div>
)

export function Heading({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <h2 className={`text-[clamp(34px,4.6vw,60px)] font-semibold leading-[1.04] tracking-[-0.032em] ${className}`}>
      {children}
    </h2>
  )
}

export function Lede({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <p className={`max-w-[46ch] text-[clamp(17px,1.5vw,20px)] leading-[1.5] text-ink-2 ${className}`}>{children}</p>
}
