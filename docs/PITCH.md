# 5-minute pitch — script, two live examples, fallbacks

Deck: `docs/pitch.html` (←/→, F fullscreen) / `docs/pitch.pdf`. Rebuild with `python docs/make_pitch.py`
(numbers come from `bench/results/*/latest.json`; it also regenerates `falconverifier/static/pipeline.svg`,
the figure shown on `/about`).

Before going on stage: open the web UI in a second tab, ⚙ → Student `Falcon 3B Arabic`, Rounds 3,
and run example 1 once so the Lean cache is warm (the second run then decides the identical claims in ~0 s
and the header says "· N from memory" — the answer itself is still freshly sampled).

| time | slide | say (one breath each) |
|---|---|---|
| 0:00 | 1 Title | "FalconVerifier: Falcon says it, Lean 4 proves it — or refutes it — in Arabic." |
| 0:20 | 2 Gap | Falcon is the region's model and its users write Arabic, but its data is mostly English; on 244 Arabic problems, Falcon 3B is right 48% of the time first try. Example: 800 AED −10% then −20% → it says 680. |
| 0:55 | 3 Idea | Truth of a math claim does not depend on language. Don't ask another LLM — translate each sentence into a Lean proposition and let the proof kernel decide. Three honest verdicts; never "probably right". |
| 1:30 | 4 Pipeline | Walk the six boxes left→right; the red dashed loop is the only thing Falcon ever sees: natural-language feedback. Memory below: verdicts are reusable, Falcon's answer is not. |
| 2:10 | 5 Arabic→Lean | Pregroup grammar: types cancel → the sentence is well-formed, and the same derivation *is* the translation. Five-friends problem → `¬ Regular f 3`, proved by the handshake lemma; nobody had to understand "friend". |
| 2:50 | 6 Live | Switch to the browser (below). |
| 4:00 | 7 Evidence | 48 → 76% on 244 problems, 92% of wrong answers caught, 0 regressions, 1 false alarm. Every row on /benchmark links to problems, traces and Lean sources. |
| 4:30 | 8 Product | Middleware: one POST adds a kernel-backed assurance score to any Falcon app; each refutation is a proof-labelled training pair (294 already). Limits said out loud. |
| 4:50 | 9 Close | "Trust in Arabic, proved in Lean." |

## Live example 1 — catch and correct (≈ 40 s)

Click the example «عربي · خصم مركب» (it fills the box and sets Expected = 576):

```
يبلغ سعر هاتف 800 درهماً. خُفِّض بنسبة 10٪ ثم خُفِّض السعر الجديد بنسبة 20٪ أخرى. ما هو السعر النهائي بالدرهم؟
```
*A phone costs 800 dirhams. It is reduced by 10%, then the new price by another 20%. What is the final price?*

- **Verify with Lean 4.** Round 1: steps appear with Arabic on the left, Lean on the right. When 3B adds the
  discounts (680) or drops a step (640), the final-answer row turns `refuted` with
  `(800:ℝ) * (1 - 0.10) * (1 - 0.20) = 576` proved by the kernel; the Arabic feedback card shows exactly
  what Falcon is told. Round 2: 576, all rows `verified`, assurance 1.0.
- **If 3B is right first time** (happens ~⅓ of the time): don't apologise — point at the green rows: "every
  sentence of its reasoning has a proof next to it; this is the product." Then open *Lean 4 source (audit)*.

## Live example 2 — prove without understanding (≈ 30 s)

Click «عربي · مصافحة» (Expected = نعم):

```
خمسة طلاب يجلسون في الفصل، ويقول كل واحد منهم إن ثلاثة من الأربعة الباقين أصدقاؤه. هل يلزم أن أحدهم يكذب؟ أجب بنعم أو لا.
```
*Five students sit in class; each says three of the other four are his friends. Must one of them be lying? Answer yes or no.*

- No LLM writes the Lean: the pregroup fragment produces `∀ f : Fin 5 → Fin 5 → Bool, ¬ Regular f 3`,
  proved via the handshake lemma (sum of degrees is even; 5·3 is odd). `verified` in ~18 s the first time.
- Run it again: the header reads "· 1 from memory", Lean latency 0.0 s, and the status line says the problem
  was seen before **and Falcon still answered afresh** — make that point explicitly.

## Fallbacks

1. Both examples right first time → still a full demo (green proofs + audit source); the correction story is
   in the recorded video and in the *replay* block at the bottom of the page.
2. Falcon endpoint slow/down → *replay* block plays recorded red→feedback→green traces with zero model calls.
3. Wi-Fi down → `docs/pitch.pdf` + the recorded video.
