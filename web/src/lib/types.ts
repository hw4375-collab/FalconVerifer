export type Verdict = 'verified' | 'refuted' | 'unknown' | 'ill_formed' | 'unverified_premise' | 'skipped'

export type SliceSummary = {
  n: number
  baseline_accuracy: number
  verified_accuracy: number
  abs_gain: number
  wrong_baseline: number
  wrong_detected_by_lean: number
  detection_recall: number | null
  false_alarms_on_correct: number
  false_alarm_rate: number | null
  fixed_after_feedback: number
  fix_rate: number | null
  regressions: number
  assured_final_answers: number
  assured_and_correct: number
  mean_rounds: number
  mean_latency_s: number
}

export type Row = {
  id: string
  tags: string[]
  expected: string | null
  base: string | null
  baseOk: boolean
  final: string | null
  finalOk: boolean
  rounds: number
  status: string
  flagged: boolean
  latency: number
}

export type Arm = {
  key: string
  run: string
  dataset: string
  lang: 'ar' | 'en'
  student: string
  formalizer: string
  maxRounds: number
  wallTime: number
  summary: Record<string, SliceSummary>
  cot: { rounds: number; steps: Partial<Record<Verdict, number>>; finals: Partial<Record<Verdict, number>> }
  rows: Row[]
  problems: Record<string, string>
}

export type Bench = { arms: Arm[] }

export type Example = {
  key: string
  kind: 'arith' | 'logic'
  title: { en: string; ar: string }
  question: string
  gloss: string | null
  student: string
  rounds: number
  latency: number
  base: string | null
  final: string | null
  source: { arm: string; run: string; id: string }
}

export type StepVerdict = {
  index: number
  verdict: Verdict
  leanProp: string | null
  text: string
  detail: string
  cached?: boolean
}

export type Round = {
  round: number
  answer: { raw: string; final: string | null; steps: { index: number; text: string }[]; latency: number }
  formalization?: {
    problemProp: string | null
    problemNote: string
    steps: { index: number; leanProp: string | null; note: string }[]
  }
  report?: {
    steps: StepVerdict[]
    final: Verdict
    finalDetail: string
    leanLatency: number
    lean: string
    cacheHits?: number
  }
  feedback: string | null
}

export type Trace = {
  problem: string
  expected: string | null
  student: string
  formalizer: string
  final: string | null
  status: string
  assurance: number
  latency: number
  rounds: Round[]
  memory?: Record<string, unknown>
}
