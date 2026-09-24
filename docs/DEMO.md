# Live demo script (≈4 minutes)

## 0. Before going on stage

```bash
cd FalconVerifer && . .venv/bin/activate && set -a && . .env && set +a
falconverifier check "(17:ℕ) * 23 = 391"        # Lean warm-up: should print verified in <10 s
falconverifier serve                             # http://localhost:8000
```

Open the web UI, pick **formalizer = falcon** (the "Falcon verifies Falcon" story) and
**rounds = 3**. Keep `docs/slides.html` open in another tab.

## 1. The hook (30 s)

> "Falcon 7B is fast and cheap, but when it is wrong it is *confidently* wrong.
> We do not ask a bigger LLM whether it is right — we ask the Lean 4 kernel."

## 2. Happy path (45 s) — trust, but verify

Paste example **"48 muffins × 7 batches − 5 boxes of 12"**. Click **Verify with Lean 4**.
Point at:

* the numbered steps Falcon produced,
* the Lean propositions next to each step (`(48:ℕ) * 7 = 336`, …),
* every row turning **verified**, the final answer **verified**, assurance score 1.0.

> "Nothing here was judged by an LLM. Each green row is a theorem Lean just proved."

## 3. The catch (90 s) — Lean catches a hallucination and *teaches*

Paste the logic example **"All doctors are educated. Some educated people are wealthy.
Does it follow that some doctors are wealthy?"** (or run the baseline-wrong problem from
`docs/BENCHMARK.md`). Show:

1. Round 1: Falcon's step that Lean **refuted** (red) — the row shows the exact proposition
   whose *negation* Lean proved.
2. The **feedback** card: natural language, quoting the step, stating what Lean proved.
   Emphasise *unknown* and *ill-formed* only produce soft hints — we never blame Falcon for
   what the formalizer or automation could not handle.
3. Round 2: Falcon revises; rows go green; final status **verified**.

> "That is the loop: Falcon reasons, Lean judges, Falcon learns — in one conversation turn."

## 4. Evidence (45 s)

Scroll to the **Benchmark** panel (or open `docs/BENCHMARK.md`):

* baseline vs verified accuracy on the standard and hard sets,
* wrong answers caught by Lean, fixed after feedback, **zero regressions**,
* false-alarm rate (why the faithfulness audit and the ℚ-lift recheck matter).

## 5. Close (30 s)

* Works with any OpenAI-compatible Falcon endpoint (TII cloud, vLLM, on-prem).
* Formalizer is pluggable: Falcon 34B today, GPT for comparison, a fine-tuned Falcon tomorrow.
* Every run leaves an **assurance trace** (`runs/*.json`): auditable, replayable evidence —
  the artefact regulated users actually need.

## Fallbacks

* Falcon endpoint slow → use `--formalizer openai` for the formalizer only; the student stays Falcon.
* No network → `falconverifier check` on hand-written propositions still demonstrates the Lean oracle,
  and `bench/results/` + `docs/BENCHMARK.md` carry the numbers.
