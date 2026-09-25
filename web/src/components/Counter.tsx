import { animate, motion, useMotionValue, useReducedMotion, useTransform } from 'motion/react'
import { useEffect } from 'react'

export function Counter({
  to,
  start,
  delay = 0,
  duration = 1.2,
  format = (v: number) => String(Math.round(v)),
  className = '',
}: {
  to: number
  start: boolean
  delay?: number
  duration?: number
  format?: (v: number) => string
  className?: string
}) {
  const reduce = useReducedMotion()
  const value = useMotionValue(reduce ? to : 0)
  const text = useTransform(value, format)
  useEffect(() => {
    if (!start) return
    if (reduce) {
      value.set(to)
      return
    }
    const controls = animate(value, to, { duration, delay, ease: [0.23, 1, 0.32, 1] })
    return () => controls.stop()
  }, [start, to, delay, duration, reduce, value])
  return <motion.span className={`num ${className}`}>{text}</motion.span>
}
