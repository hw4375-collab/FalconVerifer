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
falconverifier solve "ما هو ناتج ١٧ × ٢٣؟"                 # Arabic: pregroup grammar → Lean, no LLM formalizer
falconverifier bench --dataset bench/problems.jsonl --workers 4
falconverifier bench --dataset bench/problems_ar.jsonl --workers 4   # Arabic set
falconverifier serve            # web UI on http://localhost:8000
```

### Deploy as a public website

One Docker image bundles the server and Lean 4 + Mathlib; `deploy/` adds Caddy for HTTPS,
a per-IP rate limit, a Lean concurrency cap and an optional access token. On a fresh
Ubuntu VPS (≥ 8 GB RAM):

```bash
curl -fsSL https://raw.githubusercontent.com/hw4375-collab/FalconVerifer/main/deploy/install.sh | sudo bash
```

then fill `deploy/.env.production` and re-run (`FV_IMAGE=ghcr.io/hw4375-collab/falconverifer:latest`
pulls the CI-built image instead of compiling Mathlib). Details and the public API in
[`docs/DEPLOY.md`](docs/DEPLOY.md).

### Use it as middleware (one call from any Falcon app)

```bash
curl -s localhost:8000/api/solve -H 'content-type: application/json' \
  -d '{"problem":"ما هو ناتج ١٧ × ٢٣؟","rounds":3,"student_model":"falcon-h1-arabic-3b-instruct"}' \
  | jq '{final: .final_answer, verdict: .rounds[-1].report.final_answer_verdict, assurance: .assurance_score}'
```

The response is the full assurance trace: every round's answer, the Lean propositions,
per-step verdicts, the feedback sent back to Falcon and the kernel output.

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
| `FV_MEMORY` | `1` | `0` disables the on-disk memory (kernel verdict / translation cache, problem history) |
| `FV_MEMORY_PATH` | `runs/memory.sqlite` | where the memory lives |

### Memory: what is reused and what is never reused

Repeated (or near-identical — Arabic digits, diacritics and whitespace are normalised) questions
get faster without weakening the assurance semantics:

| remembered | key | reused how |
|---|---|---|
| Lean kernel verdicts (`verified` / `refuted` / `ill_formed` only; `unknown` is retried) | normalised proposition + tactic + fingerprint of `lean-toolchain`, `lake-manifest.json`, the Lean prelude and the scratch header | the claim is not recompiled; the step is marked `cached` and listed in the audit source |
| NL → Lean translations that type-checked | formalizer model + problem + sentence | the sentence is not sent to the formalizer; the proposition is still checked by Lean |
| problem history | normalised problem text | shows earlier sightings/status/trace paths; recalls the expected answer |

Falcon's *answer* is never reused: every run samples a fresh answer and every reported verdict is
about that answer. Hits are visible in `report.cache_hits`, `trace.memory` and `GET /api/memory`.

## Arabic track: pregroup grammar → Lean (see `docs/ARABIC.md`)

Arabic input (detected by script) goes through a **deterministic pregroup-grammar parser**
first (`falconverifier/arabic.py`): words get Lambek types (`n`, `nʳ s nˡ`, `q nˡ` …),
the type string is reduced by planar contraction, and the reduction — a proof object —
drives the construction of the Lean proposition. Steps in the supported arithmetic/logic
fragment are translated with **zero LLM calls** and carry `note: "pregroup: … → s"` in
the trace; everything else falls back to the Arabic-aware LLM formalizer. Falcon is prompted
and taught in Arabic; Eastern Arabic digits, `٫`, `٬`, `٪` are normalised.

Yes/no logic questions in the quantifier fragment («كل / بعض / لا أحد / إذا … فإن /
إما … أو», named individuals, «أطول من» orderings) are handled by a second deterministic
parser (`falconverifier/arabic_logic.py`): predicates become free `Fin 3 → Bool`, so the
closed statement is *decided* by Lean — the inference is proved, or a countermodel refutes
it — and the certificate lists every lemma identification the grammar made across
morphological variants (`B := مستطيلات ≡ المستطيلات`). The parser refuses questions whose
conclusion mentions a predicate absent from the premises, so a grammar gap is never blamed
on Falcon.

`lean/FalconVerifier/Arabic/` holds the pregroup kernel (`Pregroup.lean`), Arabic VSO/SVO
lexicon and derivations (`ArabicTypes.lean`) and the semantic theorems (`Semantics.lean`):
`vso_svo_same_meaning` (word order does not change the proposition),
`coarse_accepts_bad_agreement` (a gender-blind type accepts «كتبتْ أحمد» — the
faithfulness loss of coarse pregroups on a morphologically rich language) and
`indexed_rejects_bad_agreement` (feature-indexed atoms provably reject it, via a
derivation-invariant weight). The Python lexicon mirrors this with gender features:
«العدد ١٢ تساوي ٣» is rejected although its bare types reduce.

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
  memory.py       SQLite memory: kernel-verdict cache, translation cache, problem history
  bench.py        baseline vs verified evaluation
  cli.py / server.py   CLI and FastAPI web UI
lean/             Lake project: Mathlib + FalconVerifier/Prelude.lean (fv_auto)
bench/            dataset generator, problems.jsonl, results
```

## Security

Keys are read from the environment / `.env` only; `.env`, `runs/` and Lean caches are
git-ignored. Lean is the only component whose verdict is trusted: LLM output is never
used as evidence of correctness.
