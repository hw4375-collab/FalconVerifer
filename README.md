# FalconVerifier

**Lean 4 as a truth oracle for Falcon.** FalconVerifier wraps a Falcon LLM (default:
`falcon-h1-7b-instruct`) in a *verify-and-teach* loop: every reasoning step Falcon
produces is translated into a Lean 4 proposition, checked by the Lean kernel + Mathlib,
and any step Lean **proves false** is fed back to Falcon as a concrete correction.

```
user problem
  └─► Falcon (student)  ── numbered steps + FINAL ANSWER
        └─► Formalizer  ── each step → closed Lean 4 Prop   (Falcon 34B by default; GPT optional)
              └─► Lean 4 + Mathlib ── proves P, proves ¬P, or gives up
                    ├─ verified   → assurance ✓
                    ├─ refuted    → natural-language feedback → Falcon revises → loop
                    └─ unknown / ill-formed → soft hint only (never blamed on Falcon)
```

The output is an **assurance trace**: what Falcon said, what Lean proved, what was
taught, and a final `verified | refuted | unknown` status with an assurance score.

## Quickstart

```bash
# 1. Python
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

# 2. Lean 4 + Mathlib (one-off, ~10 min with the olean cache)
curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y
cd lean && lake exe cache get && lake build && cd ..

# 3. Keys (never committed)
cp .env.example .env   # fill FALCON_API_KEY; optionally OPENAI_API_KEY

# 4. Run
falconverifier solve "A bakery makes 48 muffins per batch. It bakes 7 batches and sells 5 boxes of 12. How many are left?"
falconverifier solve --formalizer openai "All doctors are educated. Some educated people are wealthy. Does it follow that some doctors are wealthy?"
falconverifier check "(17:ℕ) * 23 = 391" "∀ (P Q : Prop), (P → Q) → Q → P"
falconverifier bench --dataset bench/problems.jsonl --workers 4
falconverifier serve            # web UI on http://localhost:8000
```

## Configuration

| variable | default | meaning |
|---|---|---|
| `FALCON_BASE_URL` | `https://chat.falconllm.tii.ae/api` | OpenAI-compatible Falcon endpoint |
| `FALCON_API_KEY` | – | Falcon key |
| `FALCON_STUDENT_MODEL` | `falcon-h1-7b-instruct` | model under test |
| `FORMALIZER_PROVIDER` | `falcon` | `falcon` \| `openai` \| `openrouter` — who writes the Lean |
| `FALCON_FORMALIZER_MODEL` | `falcon-h1-arabic-34b-instruct` | formalizer when provider = falcon |
| `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | – | keys for the optional providers |
| `FORMALIZER_BASE_URL/_API_KEY/_MODEL` | – | full override of the formalizer endpoint |
| `MAX_ROUNDS` | `3` | verify → teach → revise rounds |
| `LEAN_PROJECT_DIR` | `./lean` | Lake project with Mathlib |

## How verification works

For each claim `P` the runner emits three theorems into one scratch file and compiles
it once with `lake env lean --json`:

```lean
theorem s1_wf  : P := by sorry        -- does P even type-check?
theorem s1_pos : P := by fv_auto      -- can Lean prove it?
theorem s1_neg : ¬ P := by fv_auto    -- can Lean prove its negation?
```

`fv_auto` is a tactic cascade (`decide`, `norm_num`, `omega`, `simp`, `tauto`,
`linarith`, `nlinarith`, `aesop`, …). Verdicts:

| pos | neg | verdict |
|---|---|---|
| ✓ | ✗ | **verified** |
| ✗ | ✓ | **refuted** → feedback |
| ✗ | ✗ | unknown (out of reach of automation; soft hint) |
| type error | – | ill-formed (formalizer repaired once, then soft hint) |

Only **refuted** claims generate strong feedback, and a refutation has to survive three
guards before it is taught:

1. **ℚ-lift recheck** — a refuted claim using `/` or `-` over ℕ/ℤ is re-proved over ℚ, so
   `(50:ℕ)/100*150 = 75` (false only because ℕ-division truncates) is not a false alarm.
2. **Literal grounding** — if every number in the Lean prop appears in Falcon's own step
   or the problem text, the refutation is pure arithmetic over Falcon's numbers and is
   accepted without asking any LLM. This is the deterministic fast path.
3. **Faithfulness audit** (only for props that introduce numbers or structure Falcon did
   not write) — the formalizer re-reads NL step vs. Lean prop, checking polarity/numbers/
   operations, and downgrades the refutation to `unknown` if the translation is unfaithful.

A fourth check runs in the other direction: if Lean **verified** `problem_prop` but the
value it computes is not the number after `FINAL ANSWER:`, the stated answer is flagged as
inconsistent with Falcon's own derivation (weak students often derive the right value and
then write a different one).

## Benchmark

`bench/problems.jsonl` holds 89 problems (51 basic math, 38 logic: syllogisms,
modus ponens/tollens, affirming the consequent, ordering, divisibility …). `falconverifier
bench` runs *baseline Falcon* and *Falcon + FalconVerifier* on the same problems and
reports per-slice: baseline accuracy, verified accuracy, absolute gain, Lean detection
recall on wrong answers, false-alarm rate on correct answers, fix rate, regressions,
mean rounds and latency. See `bench/results/` and `docs/` for the latest numbers.

## Layout

```
falconverifier/
  llm.py          OpenAI-compatible client (Falcon Open WebUI, OpenAI, OpenRouter, vLLM)
  student.py      Falcon prompt + step/answer parser
  formalizer.py   NL → Lean 4 Prop (JSON), repair, faithfulness audit
  lean_runner.py  scratch-file compilation, diagnostics → per-claim verdicts
  verifier.py     steps + final answer → VerificationReport
  feedback.py     Lean verdicts → teaching message for Falcon
  agent.py        the verify-and-teach loop, assurance trace
  bench.py        baseline vs verified evaluation
  cli.py / server.py   CLI and FastAPI web UI
lean/             Lake project: Mathlib + FalconVerifier/Prelude.lean (fv_auto)
bench/            dataset generator, problems.jsonl, results
```

## Security

Keys are read from the environment / `.env` only; `.env`, `runs/` and Lean caches are
git-ignored. Lean is the only component whose verdict is trusted: LLM output is never
used as evidence of correctness.
