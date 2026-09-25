# Lean feedback as a training signal (direction 3)

Every assurance trace in which Lean refuted a round and a later round was fully verified is a
preference pair backed by a kernel proof rather than a human or LLM judge:

| field | content |
|---|---|
| `prompt` | the original problem |
| `rejected` | the Falcon answer whose claim(s) Lean refuted (raw text) |
| `chosen` | the final answer Lean verified **and** that matches the gold answer |
| `evidence.refuted_claims` | the Lean propositions proved false (step index, step text, kernel diagnostic) |
| `evidence.feedback` | the teaching message the student received |
| `evidence.chosen_claims` | the Lean propositions verified in the chosen round |
| `meta` | language, student/formalizer model, round indices, source trace |

```bash
falconverifier export-dpo                      # bench/results + runs -> data/dpo_pairs.jsonl
falconverifier export-dpo runs/ --out x.jsonl  # specific roots
```

## Filters (all enforced in `falconverifier/dpo_export.py`)

* the chosen round must be `verified` on the final answer with no `refuted`/`ill_formed` step;
* the chosen final answer must match the trace's `expected_answer` — a Lean `verified` proves the
  *formalized* claims, so only the gold answer rules out an unfaithfully formalized claim being
  verified (traces without a gold answer are skipped unless `--allow-unlabeled`);
* the rejected round must contain at least one Lean-refuted claim (steps or final answer);
* identical (prompt, rejected) pairs are deduplicated across reruns.

## Current export

`data/dpo_pairs.jsonl`: 294 pairs (226 Arabic / 68 English) from 1038 traces, 33 duplicates dropped;
286 pairs carry one refuted claim, 8 carry two or three.

113 of the Arabic pairs come from one closed-loop pass of the 3B student over the 245-problem
scale set (`bench/make_dataset_ar_scale.py`, `bench/results/falcon3b_arabic_scale`): 238 usable
problems (6 had non-integer gold labels from a generator bug, since fixed, and are excluded),
baseline 49.2% -> verified 78.2%, 117/127 baseline errors flagged by Lean, 1 false alarm,
0 regressions, 40.8 s mean latency. Pair yield is therefore roughly one pair per two problems
the student initially gets wrong: pairs need a Lean refutation *and* a later verified, gold-matching
answer, and 44 problems hit the round limit without recovering.

## Known caveats

* `chosen` texts come from a revision round and often carry revision framing («التصحيح:», "I made
  an error…"). Before training, either strip that framing or regenerate `chosen` as a fresh answer
  conditioned on the verified claims; the Lean evidence stays attached either way.
* Almost all pairs come from the 3B student on the self-built benchmark; scaling requires new
  problems (`bench/make_dataset_ar.py` generators) and closed-loop runs.
* The formalizer's decidable fragment bounds what can become a pair: proof questions and algebra
  word problems never produce Lean evidence and are absent from the data by construction.
