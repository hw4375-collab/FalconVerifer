import type { Round, StepVerdict, Trace, Verdict } from './types'

/* eslint-disable @typescript-eslint/no-explicit-any */
type Json = Record<string, any>

export type LoopEvent =
  | { kind: 'config'; student: string; formalizer: string }
  | { kind: 'status'; message: string }
  | { kind: 'memory'; seenBefore: number; lastStatus: string; expectedRecalled: boolean }
  | { kind: 'round_start'; round: number; maxRounds: number }
  | { kind: 'student_answer'; round: number; answer: Round['answer'] }
  | { kind: 'formalized'; round: number; formalization: NonNullable<Round['formalization']> }
  | { kind: 'verified'; round: number; report: NonNullable<Round['report']> }
  | { kind: 'feedback'; round: number; feedback: string }
  | { kind: 'done'; trace: Trace }
  | { kind: 'error'; message: string }

// ---------------------------------------------------------------- server payload -> app shapes

const answerOf = (a: Json): Round['answer'] => ({
  raw: a.raw ?? '',
  final: a.final_answer ?? a.final ?? null,
  steps: a.steps ?? [],
  latency: a.latency_s ?? a.latency ?? 0,
})

const formalizationOf = (f: Json): NonNullable<Round['formalization']> => ({
  problemProp: f.problem_prop ?? f.problemProp ?? null,
  problemNote: f.problem_note ?? f.problemNote ?? '',
  steps: (f.steps ?? []).map((s: Json) => ({ index: s.index, leanProp: s.lean_prop ?? s.leanProp ?? null, note: s.note ?? '' })),
})

const reportOf = (r: Json): NonNullable<Round['report']> => ({
  steps: (r.steps ?? []).map(
    (s: Json): StepVerdict => ({
      index: s.index,
      verdict: s.verdict as Verdict,
      leanProp: s.lean_prop ?? s.leanProp ?? null,
      text: s.step_text ?? s.text ?? '',
      detail: s.detail ?? '',
      cached: !!s.cached,
    }),
  ),
  final: (r.final_answer_verdict ?? r.final) as Verdict,
  finalDetail: r.final_answer_detail ?? r.finalDetail ?? '',
  leanLatency: r.lean_latency_s ?? r.leanLatency ?? 0,
  lean: leanClaims(r.lean_file ?? r.lean ?? ''),
  cacheHits: r.cache_hits ?? r.cacheHits ?? 0,
})

const leanClaims = (src: string) =>
  src
    .split('\n')
    .filter((l) => l.startsWith('import ') || l.startsWith('theorem '))
    .join('\n')

export function traceOf(t: Json): Trace {
  if (t.rounds?.[0]?.round !== undefined) return t as Trace
  return {
    problem: t.problem,
    expected: t.expected_answer ?? null,
    student: t.student_model,
    formalizer: t.formalizer_model,
    final: t.final_answer ?? null,
    status: t.status,
    assurance: t.assurance_score,
    latency: t.total_latency_s,
    memory: t.memory,
    rounds: (t.rounds ?? []).map((r: Json) => ({
      round: r.round_index,
      answer: answerOf(r.answer),
      formalization: r.formalization ? formalizationOf(r.formalization) : undefined,
      report: r.report ? reportOf(r.report) : undefined,
      feedback: r.feedback ?? null,
    })),
  }
}

export function eventOf(kind: string, p: Json): LoopEvent | null {
  switch (kind) {
    case 'config':
      return { kind, student: p.student, formalizer: p.formalizer }
    case 'status':
      return { kind, message: p.message }
    case 'memory':
      return { kind, seenBefore: p.seen_before ?? 0, lastStatus: p.last_status ?? '', expectedRecalled: !!p.expected_answer_from_memory }
    case 'round_start':
      return { kind, round: p.round, maxRounds: p.max_rounds }
    case 'student_answer':
      return { kind, round: p.round, answer: answerOf(p.answer) }
    case 'formalized':
      return { kind, round: p.round, formalization: formalizationOf(p.formalization) }
    case 'verified':
      return { kind, round: p.round, report: reportOf(p.report) }
    case 'feedback':
      return { kind, round: p.round, feedback: p.feedback }
    case 'done':
      return { kind, trace: traceOf(p.trace) }
    case 'error':
      return { kind, message: p.message }
    default:
      return null
  }
}

// ---------------------------------------------------------------- live run over SSE

export class HttpError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function runLive(
  body: { problem: string; expected?: string; student_model?: string; rounds?: number },
  onEvent: (e: LoopEvent) => void,
  signal: AbortSignal,
) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  try {
    const token = window.localStorage.getItem('fv-token')
    if (token) headers['X-FV-Token'] = token
  } catch {
    // storage unavailable
  }
  const res = await fetch('/api/solve/stream', { method: 'POST', headers, body: JSON.stringify(body), signal })
  if (!res.ok || !res.body) {
    let msg = res.statusText
    try {
      msg = (await res.json()).detail ?? msg
    } catch {
      // not JSON
    }
    throw new HttpError(res.status, msg)
  }
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let i: number
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, i)
      buf = buf.slice(i + 2)
      const ev = /^event: (.*)$/m.exec(chunk)?.[1]
      const data = /^data: (.*)$/m.exec(chunk)?.[1]
      if (!ev || !data) continue
      const e = eventOf(ev, JSON.parse(data))
      if (e) onEvent(e)
    }
  }
}

export async function liveAvailable(): Promise<boolean> {
  if (import.meta.env.VITE_STATIC === '1') return false
  try {
    const r = await fetch('/healthz', { cache: 'no-store' })
    if (!r.ok) return false
    const h = await r.json()
    return !!(h.lean_project && h.falcon_key)
  } catch {
    return false
  }
}

// ---------------------------------------------------------------- replay of a recorded trace

const wait = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    const id = window.setTimeout(resolve, ms)
    signal.addEventListener('abort', () => {
      window.clearTimeout(id)
      reject(new DOMException('aborted', 'AbortError'))
    })
  })

export async function replay(trace: Trace, onEvent: (e: LoopEvent) => void, signal: AbortSignal, pace = 1) {
  const ms = (x: number) => x * pace
  onEvent({ kind: 'config', student: trace.student, formalizer: trace.formalizer })
  for (const r of trace.rounds) {
    onEvent({ kind: 'round_start', round: r.round, maxRounds: 3 })
    await wait(ms(1100), signal)
    onEvent({ kind: 'student_answer', round: r.round, answer: r.answer })
    await wait(ms(800), signal)
    if (r.formalization) onEvent({ kind: 'formalized', round: r.round, formalization: r.formalization })
    await wait(ms(1000), signal)
    if (r.report) onEvent({ kind: 'verified', round: r.round, report: r.report })
    if (r.feedback) {
      await wait(ms(700), signal)
      onEvent({ kind: 'feedback', round: r.round, feedback: r.feedback })
      await wait(ms(600), signal)
    }
  }
  await wait(ms(300), signal)
  onEvent({ kind: 'done', trace })
}

// ---------------------------------------------------------------- one turn of the conversation

export type Stage = 'answering' | 'formalizing' | 'checking' | 'teaching' | null

export type Turn = {
  id: string
  question: string
  gloss?: string | null
  mode: 'live' | 'replay'
  status: 'running' | 'done' | 'error' | 'stopped'
  error?: string
  student?: string
  rounds: Round[]
  stage: Stage
  stageRound: number
  maxRounds: number
  trace?: Trace
  memory?: { seenBefore: number; lastStatus: string; expectedRecalled: boolean }
  note?: string
}

export function applyEvent(turn: Turn, e: LoopEvent): Turn {
  const rounds = [...turn.rounds]
  const at = (n: number): Round =>
    rounds[n - 1] ?? { round: n, answer: { raw: '', final: null, steps: [], latency: 0 }, feedback: null }
  switch (e.kind) {
    case 'config':
      return { ...turn, student: e.student }
    case 'status':
      return { ...turn, note: e.message }
    case 'memory':
      return { ...turn, memory: { seenBefore: e.seenBefore, lastStatus: e.lastStatus, expectedRecalled: e.expectedRecalled } }
    case 'round_start':
      rounds[e.round - 1] = at(e.round)
      return { ...turn, rounds, stage: 'answering', stageRound: e.round, maxRounds: e.maxRounds }
    case 'student_answer':
      rounds[e.round - 1] = { ...at(e.round), answer: e.answer }
      return { ...turn, rounds, stage: 'formalizing', stageRound: e.round }
    case 'formalized':
      rounds[e.round - 1] = { ...at(e.round), formalization: e.formalization }
      return { ...turn, rounds, stage: 'checking', stageRound: e.round }
    case 'verified':
      rounds[e.round - 1] = { ...at(e.round), report: e.report }
      return { ...turn, rounds, stage: null, stageRound: e.round }
    case 'feedback':
      rounds[e.round - 1] = { ...at(e.round), feedback: e.feedback }
      return { ...turn, rounds, stage: 'teaching', stageRound: e.round }
    case 'done':
      return { ...turn, rounds: e.trace.rounds, trace: e.trace, status: 'done', stage: null }
    case 'error':
      return { ...turn, status: 'error', error: e.message, stage: null }
  }
}

export function cleanAnswer(raw: string): string {
  return raw
    .replace(/\$\$([\s\S]*?)\$\$/g, '$1')
    .replace(/\\\(|\\\)|\\\[|\\\]/g, '')
    .replace(/\\text\{([^}]*)\}/g, '$1')
    .replace(/\\frac\{([^}]*)\}\{([^}]*)\}/g, '$1/$2')
    .replace(/\\times/g, '×')
    .replace(/\\div/g, '÷')
    .replace(/\\cdot/g, '·')
    .replace(/\\quad|\\,|\\;/g, ' ')
    .replace(/\^\{?2\}?/g, '²')
    .replace(/\*\*/g, '')
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/`/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}
