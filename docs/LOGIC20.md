# LOGIC-20: English vs Arabic on the same 20 logic problems

Twenty logic items were sampled from the English benchmark and hand-translated
to Arabic (`bench/problems_logic20_en.jsonl`, `bench/problems_logic20_ar.jsonl`). Both
sets ran through the full loop — student `falcon-h1-arabic-3b-instruct`,
formalizer `falcon-h1-arabic-34b-instruct`, Lean 4 kernel, faithfulness audit,
up to 3 feedback rounds — after the proof-search fixes in `lean_runner.py`
(propositional counter-examples via `intros; aesop`, `∃/∀` swap models over
`Fin 3`, existential witness search).

Regenerate the table with

```bash
python bench/compare_l20.py \
  --en bench/results/l20_en/run_20260925T115156Z \
  --ar bench/results/l20_ar/run_20260925T115758Z
```

| metric | English | Arabic |
|---|---|---|
| problems / rounds | 20 / 29 | 20 / 33 |
| round-1 final answer undecided | 0/20 (0%) | 3/20 (15%) |
| round-1 final answer missing (student gave no yes/no) | 0 | 3 |
| step undecided over checkable steps | 43/77 (56%) | 16/33 (48%) |
| step refutations discarded by faithfulness audit | 39/48 (81%) | 10/15 (67%) |
| final-answer refutations discarded by audit | 0/5 (0%) | 4/14 (29%) |
| baseline correct | 15/20 (75%) | 9/20 (45%) |
| final correct | 20/20 (100%) | 16/20 (80%) |
| wrong baselines detected | 5/5 (100%) | 10/11 (91%) |
| wrong baselines fixed | 5/5 (100%) | 8/11 (73%) |
| false alarms | 2 | 1 |
| regressions (correct → wrong) | 0 | 1 |

## Reading the numbers

* **The Arabic gap is in the student, not in Lean.** Baseline accuracy drops
  75% → 45%, but the kernel still decides 85% of Arabic final answers on
  round 1, and Arabic step-level *undecided* is actually lower than English.
  Unknown did not explode to 60%+; the formalizer handles the three targeted
  structures (negation, conditional, quantifier).
* **Where Arabic still loses:** 3/20 first answers had no extractable نعم/لا
  (the 3B model answered with a sentence), and 4/14 final-answer refutations
  were discarded by the audit as unfaithful translations — i.e. the formalizer
  produced a Lean proposition that did not match the Arabic question. Those
  become `unknown`, never `refuted`.
* **Two failure modes we keep, honestly, in the traces:**
  * `l20-18-ar` — the formalizer turned "a student passed *all* exams" into
    `∃ x, ∃ y, E x y` and Lean *verified* the wrong answer. Audits only run on
    refutations; a `verified` on an LLM-translated proposition is only as good
    as that translation (deterministic pregroup steps carry a certificate,
    LLM steps do not — the UI marks the provenance).
  * `l20-08-ar` — a degenerate step formula (`P → ¬Q → … → ¬Q`, conclusion
    among premises) was refuted and fed back, confusing a correct student.
    The degenerate check now also gates step-level refutations
    (`Formalizer.audit`), not just the final answer.
* The high step-level audit discard rate (81% EN) means the 34B formalizer
  often over-claims on individual CoT sentences; the audit is doing its job,
  but it also caps how many CoT steps get a decisive verdict.

## Tokenizer

Measured with the public tokenizers on the same 20 problem statements
(measured in-session with the Hugging Face tokenizers; script not committed):

| tokenizer | English tokens | Arabic tokens | ratio |
|---|---:|---:|---:|
| Falcon3-7B | 661 | 1804 | 2.73 |
| Falcon-H1-3B | 696 | 851 | 1.22 |

The Arabic-specific Falcon-H1-Arabic tokenizer endpoint returned HTTP 401, so
its exact ratio is still **pending**; API `usage` counts are not a substitute.
With the H1 public tokenizer the Arabic/English ratio is well under 2.5, so
token-length degradation is unlikely to be the dominant factor behind the
45% baseline.
