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

`data/dpo_pairs.jsonl`: 181 pairs (113 Arabic / 68 English) from 786 traces, 33 duplicates dropped;
174 pairs carry one refuted claim, 7 carry two or three.

## Known caveats

* `chosen` texts come from a revision round and often carry revision framing («التصحيح:», "I made
  an error…"). Before training, either strip that framing or regenerate `chosen` as a fresh answer
  conditioned on the verified claims; the Lean evidence stays attached either way.
* Almost all pairs come from the 3B student on the self-built benchmark; scaling requires new
  problems (`bench/make_dataset_ar.py` generators) and closed-loop runs.
* The formalizer's decidable fragment bounds what can become a pair: proof questions and algebra
  word problems never produce Lean evidence and are absent from the data by construction.
