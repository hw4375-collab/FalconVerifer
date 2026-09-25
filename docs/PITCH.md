# 5-minute pitch — script, two live examples, fallbacks

Deck: `docs/pitch.html` (←/→, F fullscreen) / `docs/pitch.pdf`. Rebuild with `python docs/make_pitch.py`
(numbers come from `bench/results/*/latest.json`; it also regenerates the pipeline figure `docs/pipeline.svg`).

Before going on stage: open `/demo` in a second tab (the model menu defaults to Falcon-H1-Arabic 3B; live
runs use up to 3 rounds) and click **Compound discount** under *Run live* once so the Lean cache is warm (the
second run then decides the identical claims in ~0 s and the card's summary ends in "· N from memory" — the
answer itself is still freshly sampled).

| time | slide | say (one breath each) |
|---|---|---|
| 0:00 | 1 Title | "FalconVerifier: Falcon says it, Lean 4 proves it — or refutes it — in Arabic." |
| 0:20 | 2 Gap | Falcon is the region's model and its users write Arabic, but its data is mostly English; on 244 Arabic problems, Falcon 3B is right 48% of the time first try. Example: 800 AED −10% then −20% → it says 680. |
| 0:55 | 3 Idea | Truth of a math claim does not depend on language. Don't ask another LLM — translate each sentence into a Lean proposition and let the proof kernel decide. Three honest verdicts; never "probably right". |
| 1:30 | 4 Pipeline | Walk the six boxes left→right; the red dashed loop is the only thing Falcon ever sees: natural-language feedback. Memory below: verdicts are reusable, Falcon's answer is not. |
| 2:10 | 5 Arabic→Lean | Pregroup grammar: types cancel → the sentence is well-formed, and the same derivation *is* the translation. Five-friends problem → `¬ Regular f 3`, proved by the handshake lemma; nobody had to understand "friend". |
| 2:50 | 6 Live | Switch to the browser (below). |
| 4:00 | 7 Evidence | 48 → 76% on 244 problems, 92% of wrong answers caught, 0 regressions, 1 false alarm. Every question on /results replays its trace, each claim with its Lean proposition. |
| 4:30 | 8 Product | Middleware: one POST adds a kernel-backed assurance score to any Falcon app; each refutation is a proof-labelled training pair (294 already). Limits said out loud. |
| 4:50 | 9 Close | "Trust in Arabic, proved in Lean." |

## Live example 1 — catch and correct (≈ 40 s)

Click **Compound discount** under *Run live* (it runs with Expected = 576):

```
يبلغ سعر هاتف 800 درهماً. خُفِّض بنسبة 10٪ ثم خُفِّض السعر الجديد بنسبة 20٪ أخرى. ما هو السعر النهائي بالدرهم؟
```
*A phone costs 800 dirhams. It is reduced by 10%, then the new price by another 20%. What is the final price?*

- **Two answers side by side.** The left card is Falcon's answer as given; the right card follows the loop:
  Falcon round 1 → Lean 4 ✕ → correction → Falcon round 2 → Lean 4 ✓. When 3B adds the discounts (680) or
  drops a step (640), round 1 is `refuted` with `(800:ℝ) * (1 - 0.10) * (1 - 0.20) = 576` proved by the
  kernel. *Show the proof* lists every claim with its Lean proposition and the exact Arabic correction Falcon
  was sent. Round 2: 576, every claim proved.
- **If 3B is right first time** (happens ~⅓ of the time): don't apologise — open *Show the proof*: "every
  sentence of its reasoning has a proof next to it; this is the product." Then open *Lean source sent to the
  kernel*.

## Live example 2 — prove without understanding (≈ 30 s)

Click **Five friends** under *Run live* (Expected = نعم):

```
خمسة طلاب يجلسون في الفصل، ويقول كل واحد منهم إن ثلاثة من الأربعة الباقين أصدقاؤه. هل يلزم أن أحدهم يكذب؟ أجب بنعم أو لا.
```
*Five students sit in class; each says three of the other four are his friends. Must one of them be lying? Answer yes or no.*

- No LLM writes the Lean: the pregroup fragment produces `∀ f : Fin 5 → Fin 5 → Bool, ¬ Regular f 3`,
  proved via the handshake lemma (sum of degrees is even; 5·3 is odd). `verified` in ~18 s the first time.
- Run it again: the summary ends in "· 1 from memory", the reused verdict is marked *from memory* in the
  proof, and the card says the problem was seen before **and Falcon still answered afresh** — make that point
  explicitly.

## Fallbacks

1. Both examples right first time → still a full demo (green proofs + audit source); the correction story is
   in the recorded video and in *Recorded runs* in the demo sidebar.
2. Falcon endpoint slow/down → *Recorded runs* in the demo sidebar replay red→correction→green traces with
   zero model calls.
3. Wi-Fi down → `docs/pitch.pdf` + the recorded video.
