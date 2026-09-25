import { useEffect, useState } from 'react'
import type { Bench, Example, Trace } from './types'

export const BASE = import.meta.env.BASE_URL

const cache = new Map<string, Promise<unknown>>()

function load<T>(url: string): Promise<T> {
  let p = cache.get(url) as Promise<T> | undefined
  if (!p) {
    p = fetch(url).then((r) => {
      if (!r.ok) throw new Error(`${r.status} ${url}`)
      return r.json() as Promise<T>
    })
    p.catch(() => cache.delete(url))
    cache.set(url, p)
  }
  return p
}

export const loadBench = () => load<Bench>(`${BASE}data/bench.json`)
export const loadExamples = () => load<{ examples: Example[] }>(`${BASE}data/examples.json`).then((d) => d.examples)
export const loadExampleTrace = (key: string) => load<Trace>(`${BASE}data/traces/${key}.json`)

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<{ data?: T; error?: Error }>({})
  useEffect(() => {
    let alive = true
    fn().then(
      (data) => alive && setState({ data }),
      (error: Error) => alive && setState({ error }),
    )
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return state
}

export const pct = (x: number | null | undefined, digits = 0) =>
  x == null ? '–' : `${(x * 100).toFixed(digits)}%`

export const MODEL_LABEL: Record<string, string> = {
  'falcon-h1-arabic-3b-instruct': 'Falcon-H1-Arabic 3B',
  'falcon-h1-7b-instruct': 'Falcon-H1 7B',
  'falcon-h1r-7b': 'Falcon-H1R 7B',
  'falcon-h1-arabic-34b-instruct': 'Falcon-H1-Arabic 34B',
}

export const modelLabel = (m: string) => MODEL_LABEL[m] ?? m
