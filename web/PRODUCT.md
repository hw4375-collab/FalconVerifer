# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: Vite + React + TypeScript single-page app in `web/` (Tailwind v4, Motion), built into
`falconverifier/static/` and served by the existing FastAPI server. Benchmark results and the demo
traces are exported to static JSON at build time, so the site also runs with no backend.
(Inferred from the brief; the user asked for a from-scratch site and delegated the plan.)

## Users

- Hackathon judges watching a short live pitch on a projector, then browsing on their own
  laptops or phones. They know AI, not necessarily Lean or pregroup grammars. (inferred)
- The presenting team driving the demo live, under time pressure, on venue Wi-Fi.

## Product Purpose

NYU Falcon, built on the FalconVerifier engine, sits between Falcon (TII's Arabic-native LLM) and the user. Every reasoning step and
the final answer are translated into Lean 4 propositions; the Lean kernel proves or refutes each one;
refuted claims go back to Falcon as a correction in its own language, and Falcon answers again.
Success on this site: within a minute a visitor understands that Falcon's Arabic math and logic
errors are caught by a proof kernel, not by another model, and are fixed.

## Positioning

- The Lean 4 kernel is the only judge. LLMs generate; they are never evidence.
- Falcon verifies Falcon: the formalizer is Falcon-H1-Arabic-34B, the student a small Falcon.
- For the covered Arabic fragment a pregroup grammar translates with zero LLM calls; its
  derivation is the certificate that the translation is faithful.
- Outside the decidable fragment the answer is "unknown", never a guess.

## Operating Context

- Live loop: 10-40 s per round, up to 3 rounds (mean ~40 s per problem for the 3B student).
- A live run needs `FALCON_API_KEY` and a built Lean 4 + Mathlib project; recorded traces in
  `bench/results/` replay the same loop with zero model calls.
- API: `POST /api/solve/stream` (SSE events config, round_start, student_answer, formalized,
  verified, feedback, done), `GET /api/bench/runs`, `GET /api/bench/trace/{arm}/{run}/{id}`, `/healthz`.

## Capabilities and Constraints

- Verdicts: verified, refuted, unknown, ill_formed, skipped.
- Students: `falcon-h1-arabic-3b-instruct`, `falcon-h1-7b-instruct`, `falcon-h1r-7b`.
- Arabic and English input, right-to-left rendering, Eastern Arabic digits normalized.
- Covered fragments: arithmetic and percentages, quantifier logic (syllogisms, conditionals,
  orderings), symmetric relations and counting (handshake lemma).

## Brand Commitments

- Name: NYU Falcon; the repository, Python package and CLI keep the engine's name (FalconVerifier,
  `falconverifier`). Team: ChaosButterfly, whose butterfly is the product mark.
- From the brief: minimal, diagrams and arrows instead of paragraphs, scroll-driven and ambient
  animation, very presentable on stage. No purple gradients, no templated "vibe-coded" look, no
  explanatory clutter in the UI.
- Falcon and TII are named as the models under test; the site must not look like an official TII
  property.

## Evidence on Hand

- `bench/results/*/run_*/results.json` and per-problem assurance traces (8 arms).
- Falcon-H1-Arabic-3B, 86 Arabic problems: 58.1% to 88.4%, 33 of 36 wrong answers caught by
  Lean, 26 fixed, 1 false alarm, 0 regressions.
- Same student, 244-problem Arabic scale set: 47.9% to 76.2%, 117 of 127 caught, 0 regressions.
- Falcon-H1-7B control on the Arabic set: 97.4% to 98.7%.
- `data/dpo_pairs.jsonl`: 294 Lean-refuted to Lean-verified preference pairs (226 Arabic). Training
  on them has not been run; any fine-tuning result must not be claimed.

## Product Principles

1. Show the proof, not an adjective: every verdict comes with the Lean proposition it judged.
2. Arabic first: Arabic is primary content, set right-to-left, with an English gloss beside it.
3. Honest boundaries: unknown stays unknown; a replayed run is labelled as recorded.
4. Every number traces back to a committed results file.

## Accessibility & Inclusion

- Bilingual interface (English and Arabic, full right-to-left layout).
- Projector legibility: large type, high contrast, no meaning carried by color alone.
- Reduced-motion preference collapses all scroll choreography to static frames.
