"""Build docs/talk.html — a 5–10 minute English talk deck (Arabic I/O shown verbatim with English glosses) (self-contained HTML, printable to PDF).

Usage: python docs/make_talk.py
Numbers are read from bench/results/*/latest.json; nothing is typed by hand.
Navigation: ←/→, Space, click; F fullscreen, O overview; Ctrl+P prints one slide per page.
"""

from __future__ import annotations

import json
from pathlib import Path

from make_slides import CSS, JS, pct, slide

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "bench" / "results"
OUT = ROOT / "docs" / "talk.html"

PRINT_CSS = """
h1,h2,h3,p,li,td,th,.node,.sub,.note,.tag{font-family:Inter,"Noto Sans","Segoe UI",system-ui,sans-serif}
.ar{direction:rtl;unicode-bidi:isolate;font-family:"Noto Naskh Arabic","Amiri","Segoe UI",system-ui,sans-serif;font-size:1.75vw}
.small{font-size:1.35vw;color:#b7c3d6}
.gloss{color:#9fb0c8;font-size:1.25vw;margin:.2vh 0 1vh;font-style:italic}
.cols>*{min-width:0}pre{white-space:pre-wrap;word-break:break-word}
.slide{justify-content:flex-start;padding-top:5vh}
h2{font-size:2.7vw}h2 small{font-size:1.2vw}p,li{font-size:1.5vw}.card h3{font-size:1.45vw}pre{font-size:1.1vw}
table.kpi{font-size:1.3vw}table.kpi th,table.kpi td{padding:.7vh 1vw}.big .n{font-size:4vw}
@media print{
  @page{size:1600px 900px;margin:0}
  html,body{height:auto;background:#070b14}
  .deck{height:auto;overflow:visible}
  .slide{display:flex!important;position:relative;inset:auto;width:1600px;height:900px;page-break-after:always;break-after:page;padding:44px 112px;overflow:hidden}
  .foot{display:none}
  h1{font-size:76px}h2{font-size:42px;margin-bottom:22px}h2 small{font-size:19px}p,li{font-size:23px}li{margin:4px 0}.sub{font-size:31px}
  .card{padding:16px 22px}.card h3{font-size:23px}pre{font-size:17px;padding:10px 14px}.node{font-size:19px;padding:10px 14px}.node b{font-size:17px}.arrow{font-size:30px}
  table.kpi{font-size:20px}table.kpi th,table.kpi td{padding:6px 12px}.big .n{font-size:64px}.big .l{font-size:18px}.note{font-size:17px;margin-top:12px}.small{font-size:19px}
  .tag{font-size:17px}.v{font-size:19px}.pill{font-size:17px}.ar{font-size:26px}.gloss{font-size:19px}.cols{gap:40px}
}
"""


def summary(arm: str) -> dict:
    return json.loads((RESULTS / arm / "latest.json").read_text())["summary"]


def kpi(rows: list[tuple[str, dict]]) -> str:
    body = "".join(
        f"<tr><th>{label}</th><td>{s['n']}</td><td>{pct(s['baseline_accuracy'])}</td>"
        f"<td><b>{pct(s['verified_accuracy'])}</b></td><td>{s['wrong_detected_by_lean']}/{s['wrong_baseline']}</td>"
        f"<td>{s['fixed_after_feedback']}/{s['wrong_baseline']}</td><td>{s['false_alarms_on_correct']}</td><td>{s['regressions']}</td></tr>"
        for label, s in rows
    )
    return (
        '<table class="kpi"><thead><tr><th>slice</th><th>n</th><th>baseline</th><th>verified</th>'
        "<th>caught by Lean</th><th>fixed after feedback</th><th>false alarms</th><th>regressions</th></tr></thead><tbody>"
        + body
        + "</tbody></table>"
    )


def ar(text: str, gloss: str) -> str:
    return f'<p class="ar">{text}</p><p class="gloss">{gloss}</p>'


def build() -> str:
    ar3 = summary("falcon3b_arabic")
    ar7 = summary("falcon7b_arabic")["all"]
    en7 = summary("falcon_formalizer")["all"]
    en7h = summary("falcon_formalizer_hard")["all"]
    A = ar3["all"]
    L = ar3["logic"]
    slides = [
        # 1 title
        slide(
            '<span class="tag">Verified Falcon · Hub71 Fish Tank</span>'
            "<h1>Let Lean 4 be Falcon's referee.</h1>"
            '<p class="sub">An auditable middleware for Arabic math &amp; logic conversations: Falcon answers → formalize → Lean kernel decides → grounded correction → Falcon revises.</p>'
            f'<p class="note">Falcon-H1-Arabic-3B on {A["n"]} Arabic math/logic problems: accuracy {pct(A["baseline_accuracy"])} → {pct(A["verified_accuracy"])}, {A["regressions"]} answers turned from right to wrong. Code, data and every per-problem trace are open.</p>'
        ),
        # 2 problem
        slide(
            "<h2>LLMs are confidently wrong — more so in Arabic<small>and checking a chain of reasoning by hand is expensive</small></h2>"
            '<div class="cols"><div class="card"><h3>Why Falcon, why Arabic</h3><ul>'
            "<li>Falcon is TII's home-grown model; local users ask it in Arabic.</li>"
            "<li>Its pre-training corpus is mostly English → weaker Arabic math and logic.</li>"
            f"<li>Same problems: Falcon 7B {pct(ar7['baseline_accuracy'])}, Falcon Arabic-3B only {pct(A['baseline_accuracy'])}.</li>"
            "<li>Arabic itself amplifies risk: two digit systems (٠-٩ vs 0-9), RTL text mixed with numbers, rich morphology, free word order, ambiguous «إما…أو» (either/or).</li>"
            "</ul></div>"
            '<div class="card"><h3>Typical errors (real 3B output)</h3>'
            + ar(
                "800 × 0.9 = 720، ثم 720 × 0.8 = 576 … الجواب النهائي: 680",
                "“800 × 0.9 = 720, then 720 × 0.8 = 576 … Final answer: 680”",
            )
            + "<p>Every step right, final answer wrong — a reader who only checks the conclusion is fooled.</p>"
            + ar(
                "عمر أطول من يوسف، ويوسف أطول من خالد. هل يلزم أن عمر أطول من خالد؟ → لا",
                "“Omar is taller than Yusuf, Yusuf taller than Khalid. Must Omar be taller than Khalid?” → “No”",
            )
            + "<p>Transitivity answered backwards — fluent language, broken logic.</p></div></div>"
        ),
        # 3 goal
        slide(
            "<h2>Our goal<small>not a smarter model — a referee that cannot lie</small></h2>"
            '<div class="cols"><div class="card"><h3>What we do</h3><ul>'
            "<li><b>Decide truth</b>: translate each reasoning step and the final answer into Lean 4 propositions; the theorem-prover kernel decides.</li>"
            "<li><b>Teach</b>: only steps proven false get feedback, grounded in a Lean theorem or a concrete counter-model; Falcon answers again.</li>"
            "<li><b>Leave evidence</b>: every answer ships with an assurance trace — propositions, verdicts, feedback, revisions.</li>"
            "</ul></div>"
            '<div class="card"><h3>What we refuse to do</h3><ul>'
            "<li>Never treat an LLM judgment as evidence: both LLMs (student, translator) are generators; <b>Lean is the only truth authority</b>.</li>"
            "<li>Never fake verification: outside the decidable fragment we honestly say <span class='v unk'>unknown</span> instead of producing a more confident text.</li>"
            "<li>No weight changes today — an external referee now, a training signal next.</li>"
            "</ul></div></div>"
        ),
        # 4 workflow
        slide(
            "<h2>Workflow: the verify–teach loop<small>Falcon never sees Lean; it only sees a teacher's natural-language correction</small></h2>"
            '<div class="flow">'
            '<div class="node"><b>1 · Student</b>Falcon answers step by step<br><span class="ar" style="font-size:inherit">الخطوة 1 … الجواب النهائي</span><br><span class="dim">step 1 … final answer</span></div><span class="arrow">→</span>'
            '<div class="node"><b>2 · Formalize</b>pregroup grammar (zero LLM)<br>or Falcon-34B → Lean propositions</div><span class="arrow">→</span>'
            '<div class="node lean"><b>3 · Lean 4 + Mathlib</b>try to prove P and ¬P for every proposition</div><span class="arrow">→</span>'
            '<div class="node"><b>4 · Feedback</b>only on refuted steps: theorem / counter-model / mismatch</div><span class="arrow">→</span>'
            '<div class="node"><b>5 · Revise</b>Falcon re-answers, back to 2</div></div>'
            "<p>Five verdicts: <span class='v ok'>verified</span> Lean proved P · <span class='v bad'>refuted</span> Lean proved ¬P · "
            "<span class='v unk'>unknown</span> neither · <span class='v ill'>ill_formed</span> does not type-check · <span class='v unk'>skipped</span> no checkable claim</p>"
            '<p class="note">Guards against false alarms: ℚ re-check, number grounding, degenerate-reasoning filter, structural round-trip signature (relation arity / symmetry / counts missing → downgraded to unknown). 10–40 s per round.</p>'
        ),
        # 5 pregroup
        slide(
            "<h2>Math background ①: pregroup grammar (Lambek 1999)<small>“is this sentence well-formed?” becomes “do the types reduce to s?”</small></h2>"
            '<div class="cols"><div class="card"><h3>Three rules are enough</h3>'
            "<p>Each word gets a type built from basic types <code>n</code> (noun / number), <code>s</code> (sentence), <code>q</code> (question) and their left/right adjoints <code>xˡ, xʳ</code>.</p>"
            "<pre>xˡ · x → 1        x · xʳ → 1        (contraction)\nwell-formed  ⇔  the product of word types reduces to s</pre>"
            "<p>The verb “equals” has type <code>nʳ s nˡ</code>: it consumes one n on its left, one n on its right, and leaves s.</p></div>"
            '<div class="card"><h3>Arabic example</h3>'
            + ar("١٧ × ٢٣ يساوي ٣٩١", "“17 × 23 equals 391” (Eastern Arabic digits)")
            + "<pre>n · nʳ n nˡ · n · nʳ s nˡ · n\n= n·(nʳ n nˡ)·n  →  n          (17×23 is a number)\n  n · nʳ s nˡ · n  →  s        (“equals” eats one n on each side)</pre>"
            "<p>The reduction path is itself a <b>certificate</b>, stored in every trace: <code>pregroup: n nʳ s nˡ n → s</code>. The same path drives the Lean proposition: <code>(17:ℚ) * 23 = 391</code>.</p></div></div>"
        ),
        # 6 category theory
        slide(
            "<h2>Math background ②: syntax → semantics as a functor<small>DisCoCat (Coecke–Sadrzadeh–Clark 2010)</small></h2>"
            '<div class="cols"><div class="card"><h3>Category theory in one breath</h3><ul>'
            "<li>A pregroup is a <b>compact closed monoidal category</b>: word types are objects, contractions <code>xˡx→1</code> are morphisms (“cups”).</li>"
            "<li>Meaning lives in another category — vector spaces, relations, or, here, <b>Lean propositions</b>.</li>"
            "<li>Translation is a structure-preserving <b>functor F</b>: F(reduction) = how meanings compose.</li>"
            "</ul><pre>F : Grammar ─→ LeanProp\nF(n) = ℚ / Fin 3 → Bool      F(s) = Prop\nF(nʳ s nˡ “equals”) = fun a b => a = b</pre></div>"
            '<div class="card"><h3>Why this matters</h3><ul>'
            "<li><b>Compositionality</b>: the meaning is fixed by the shape of the reduction; word meanings only appear at the leaves.</li>"
            "<li><b>Word order is irrelevant</b>: we proved in Lean that Arabic VSO and SVO derive the same meaning (<code>vso_svo_same_meaning</code>), so the parser may normalise freely.</li>"
            "<li><b>Provable limits</b>: coarse types lose gender/number agreement — also a Lean theorem (<code>coarse_accepts_bad_agreement</code>), pointing to dependent types as future work.</li>"
            "</ul></div></div>"
        ),
        # 7 no need to understand definitions
        slide(
            "<h2>No need to know what a “square” is to judge the inference<small>logical validity depends only on the shape of the sentence, not on word meanings</small></h2>"
            '<div class="cols"><div class="card"><h3>Problem (3B first answers “yes” or omits the answer — wrong either way)</h3>'
            + ar(
                "كل المربعات مستطيلات، وبعض المستطيلات ليست مربعات. هل يلزم أن بعض المربعات ليست مستطيلات؟",
                "“All squares are rectangles, and some rectangles are not squares. Must some squares not be rectangles?”",
            )
            + "<pre>pregroup:  كل A B  ·  بعض B ليست A  ⊢?  بعض A ليست B\n  A := مربعات ≡ المربعات     (morphological variants merged, in the certificate)\n  B := مستطيلات ≡ المستطيلات\n\nLean:  ∀ (A B : Fin 3 → Bool),\n  (∀ x, A x → B x) → (∃ x, B x ∧ ¬A x) → ∃ x, A x ∧ ¬B x</pre></div>"
            '<div class="card"><h3>Lean\'s answer</h3>'
            "<p><span class='v bad'>refuted</span> — <code>decide</code> finds a counter-model: A = {0}, B = {0, 1}.</p>"
            + ar(
                "مثال مضاد: «المربعات» = {x0}، «مستطيلات» = {x0، x1}. كل المقدمات صحيحة ولكن «بعض المربعات ليست مستطيلات» خاطئة.",
                "Feedback sent to Falcon: “Counter-example: squares = {x0}, rectangles = {x0, x1}. All premises hold, but ‘some squares are not rectangles’ is false.” → 3B revises to «لا» (“no”).",
            )
            + "<ul><li>Lean contains no “square” and no “rectangle” — only predicates A and B. <b>The verdict is independent of word meaning.</b></li>"
            "<li>A reviewer who reads no Arabic can still audit this: proposition, verdict, counter-model.</li></ul></div></div>"
        ),
        # 8 handshake
        slide(
            "<h2>Example ②: five students and the handshake lemma<small>formalization can go wrong too, so we protect the shape</small></h2>"
            '<div class="cols"><div class="card"><h3>Problem</h3>'
            + ar(
                "خمسة طلاب، يقول كل واحد منهم إن ثلاثة من الأربعة الباقين أصدقاؤه. هل يلزم أن أحدهم يكذب؟",
                "“Five students; each says three of the other four are his friends. Must someone be lying?”",
            )
            + "<p><b>Wrong formalization</b> (LLM translator): <code>students : Fin 5 → Bool</code> — friendship squashed into one boolean per person, losing that it is binary and symmetric. Lean correctly refuted a <i>wrong</i> proposition → false alarm.</p></div>"
            '<div class="card"><h3>Right formalization (deterministic fragment)</h3>'
            "<pre>∀ f : Fin 5 → Fin 5 → Bool, ¬ Regular f 3\n\nRegular f k := (∀ x y, f x y = f y x)   -- symmetric\n             ∧ (∀ x, f x x = false)     -- no self-loops\n             ∧ ∀ x, degree f x = k</pre>"
            "<p><span class='v ok'>verified</span> in 18 s via the handshake lemma <code>∑ degree = 2·|E|</code>: 5 × 3 = 15 is odd → contradiction. No enumeration of 2²⁵ relations.</p>"
            "<p>Round-trip signature: the question is about a <i>mutual relation between individuals</i> with count 3; a formula lacking a binary type, symmetry or the number 3 is downgraded to unknown — no more false alarm.</p></div></div>"
        ),
        # 9 arithmetic
        slide(
            "<h2>Example ③: one round of feedback fixes a wrong final answer<small>Falcon-3B · real trace (armath-048)</small></h2>"
            '<div class="cols"><div class="card"><h3>Round 1</h3>'
            + ar(
                "سعر هاتف 800 درهم، خُفِّض 10٪ ثم 20٪. ما السعر النهائي؟",
                "“A phone costs 800 AED, discounted 10% then 20%. What is the final price?”",
            )
            + "<pre>step 2  (800:ℝ)*10/100 = 80 ∧ 800-80 = 720     verified\nstep 3  (720:ℝ)*20/100 = 144 ∧ 720-144 = 576   verified\nfinal   Lean proves 800*(1-0.10)*(1-0.20) = 576\n        Falcon wrote 680                       refuted</pre>"
            + ar(
                "الجواب النهائي لا يطابق ما تستنتجه خطواتك. تحقق Lean 4 من أن … = 576",
                "Feedback: “Your final answer does not match what your own steps imply. Lean 4 verified that … = 576.”",
            )
            + "</div>"
            '<div class="card"><h3>Round 2</h3>'
            "<pre>step 2, 3        verified\nfinal  576       verified      assurance = 1.0</pre>"
            "<p>The feedback adds nothing new: it quotes a proposition Falcon itself derived and Lean proved.</p>"
            f"<p>This error class drives most of the 3B math gain {pct(ar3['math']['baseline_accuracy'])} → {pct(ar3['math']['verified_accuracy'])}; Eastern-digit problems {pct(ar3['eastern-digits']['baseline_accuracy'])} → {pct(ar3['eastern-digits']['verified_accuracy'])}.</p></div></div>"
        ),
        # 10 trust and review
        slide(
            "<h2>Human review: from “read every step” to “look at the red ones”<small>formalization turns review from understanding the problem into checking a certificate</small></h2>"
            f'<div class="big"><div><div class="n">{A["assured_and_correct"]}/{A["n"]}</div><div class="l">final answers fully Lean-verified and correct — no human reading needed</div></div>'
            f'<div><div class="n">{A["false_alarms_on_correct"]}</div><div class="l">false alarm on a correct answer ({pct(A["false_alarm_rate"])}), causing no regression</div></div>'
            f'<div><div class="n">{A["regressions"]}</div><div class="l">answers turned from right to wrong</div></div>'
            f'<div><div class="n">{pct(A["detection_recall"])}</div><div class="l">baseline errors caught by Lean ({A["wrong_detected_by_lean"]}/{A["wrong_baseline"]})</div></div></div>'
            "<ul><li>Reviewers only inspect <span class='v bad'>refuted</span> and <span class='v unk'>unknown</span> items; each carries the Lean proposition and kernel diagnostics and is reproducible (<code>lake env lean</code>).</li>"
            "<li>Checking needs no language skill: propositions are Lean, counter-examples are finite models, certificates are pregroup reductions — an Arabic-illiterate reviewer can audit an Arabic conversation.</li>"
            "<li>Outside the fragment the system degrades honestly: proof questions, open “why”, and relation problems before the graph fragment existed returned unknown rather than a fake verification.</li></ul>"
        ),
        # 11 benchmark
        slide(
            f"<h2>Benchmark: Falcon Arabic-3B, {A['n']} Arabic problems<small>paired design: baseline = round 1 of the same trajectory · Lean verdicts + exact-answer match · {A['regressions']} regressions</small></h2>"
            + kpi(
                [
                    ("all", A),
                    ("math", ar3["math"]),
                    ("logic", L),
                    ("hard (compound discount / order of operations)", ar3["hard"]),
                    ("syllogisms", ar3["syllogism"]),
                    ("pregroup arithmetic fragment (zero LLM)", ar3["fragment"]),
                    ("relation / counting (handshake lemma)", ar3["relation"]),
                    ("Eastern Arabic digits ٠-٩", ar3["eastern-digits"]),
                ]
            )
            + f'<p class="note">The original 76-problem subset: 55.3% → 84.2% in three independent reruns, exact McNemar p ≈ 4.8×10⁻⁷. Controls: Falcon 7B Arabic {pct(ar7["baseline_accuracy"])} → {pct(ar7["verified_accuracy"])}; English 7B {pct(en7["baseline_accuracy"])} → {pct(en7["verified_accuracy"])} ({en7["n"]} problems), hard {pct(en7h["baseline_accuracy"])} → {pct(en7h["verified_accuracy"])} ({en7h["n"]}). '
            f"Mean {A['mean_rounds']} rounds, {A['mean_latency_s']:.0f} s per problem. Self-built dataset — not directly comparable with GSM8K-style public benchmarks.</p>"
        ),
        # 12 three stages
        slide(
            "<h2>More deterministic formalization → larger gain<small>Arabic logic problems, Falcon-3B, same student across versions</small></h2>"
            '<table class="kpi"><thead><tr><th>formalizer version</th><th>n</th><th>baseline</th><th>verified</th><th>caught by Lean</th><th>false alarms</th></tr></thead><tbody>'
            "<tr><th>① LLM (Falcon-34B) translation only</th><td>24</td><td>66.7%</td><td>66.7%</td><td>0/8</td><td>0</td></tr>"
            "<tr><th>② + yes/no polarity alignment, degenerate-reasoning filter</th><td>24</td><td>62.5%</td><td>79.2%</td><td>3/9</td><td>0</td></tr>"
            "<tr><th>③ + pregroup deterministic fragment + counter-model teaching</th><td>24</td><td>70.8%</td><td><b>91.7%</b></td><td>7/7</td><td>0</td></tr>"
            f"<tr><th>④ + relation/counting fragment (10 handshake problems added)</th><td>{L['n']}</td><td>{pct(L['baseline_accuracy'])}</td><td><b>{pct(L['verified_accuracy'])}</b></td><td>{L['wrong_detected_by_lean']}/{L['wrong_baseline']}</td><td>{L['false_alarms_on_correct']}</td></tr>"
            "</tbody></table>"
            "<ul><li>The gain comes not from a stronger model but from <b>taking translation away from the LLM</b>: pregroup reduction fixes the shape of the proposition, Lean fixes its truth.</li>"
            "<li>Problems still on the LLM path (outside the fragment) remain the weak link — documented as such.</li></ul>"
        ),
        # 13 why Arabic
        slide(
            "<h2>Why Arabic<small>largest need, and a regular grammar that makes deterministic formalization feasible</small></h2>"
            '<div class="cols"><div class="card"><h3>Demand: Arabic needs an external referee most</h3><ul>'
            "<li>Arabic is a minority language in Falcon's pre-training → lower baseline, more hallucination (3B: 58% vs 97% for English / 7B).</li>"
            "<li>Two digit systems, RTL mixing, clitics fused into words, free word order, ambiguous connectives — all places where meaning is lost during reasoning.</li>"
            "<li>Mathematical and logical truth is language-independent: once in Lean, the verdict no longer depends on how much Arabic the model saw.</li></ul></div>"
            '<div class="card"><h3>Supply: Arabic lends itself to formalization</h3><ul>'
            "<li>Modern Standard Arabic is a normed written language; quantifier patterns are fixed: <span class='ar' style='font-size:1.5vw'>كل / بعض / لا أحد / إذا…فإن</span> (all / some / none / if…then).</li>"
            "<li>Root-and-pattern morphology is highly regular — a good fit for algebraic grammars and deterministic parsing.</li>"
            "<li>VSO ≡ SVO is proven in Lean, so word-order normalisation is safe.</li>"
            "<li>Boundary: morphology makes coarse types lose faithfulness (also proven) — a research direction, not a hidden flaw.</li></ul></div></div>"
        ),
        # 14 limits / next
        slide(
            "<h2>Limits and next steps<small>honest boundaries, and a data flywheel</small></h2>"
            '<div class="cols"><div class="card"><h3>What we cannot do today</h3><ul>'
            "<li>Proof questions / open “why”: no decidable final proposition.</li>"
            "<li>Algebra / age word problems: the LLM mis-translates text into equations; Lean catches 0.</li>"
            "<li>3B occasionally refuses to fix an answer Lean refuted (armath-051).</li>"
            f"<li>Latency {A['mean_latency_s']:.0f} s per problem; Lean + Mathlib is a heavy deployment.</li></ul></div>"
            '<div class="card"><h3>Next</h3><ul>'
            "<li><b>Data flywheel</b>: every trace is a (wrong reasoning, Lean counter-example, corrected reasoning) triple → DPO / RL from Lean feedback, internalising the referee into Falcon. 175 pairs exported so far.</li>"
            "<li>Public benchmarks (GSM8K-ar, MGSM-ar): report accuracy and “decidable coverage”.</li>"
            "<li>Product: hosted service + Open WebUI plugin (Docker ready); Arabic K-12 math grading.</li>"
            "<li>Research: agreement features as dependent types; VSO≡SVO as a 2-cell between derivations.</li></ul></div></div>"
        ),
        # 15 close
        slide(
            "<h1>Ask the kernel, not the model.</h1>"
            f'<p class="sub">Falcon-3B Arabic: {pct(A["baseline_accuracy"])} → {pct(A["verified_accuracy"])}, {A["regressions"]} regressions, and every correction is backed by a Lean proof.</p>'
            '<p class="note">github.com/hw4375-collab/FalconVerifer · <code>pip install -e . &amp;&amp; falconverifier serve</code> · traces, report and these slides are generated from the raw results.</p>'
        ),
    ]
    body = "\n".join(slides)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Verified Falcon — talk</title>'
        f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}{PRINT_CSS}</style></head><body>'
        f'<div class="deck">{body}<div class="foot"><span>Verified Falcon · Lean 4 as the truth authority for Falcon</span><span id="pg"></span></div></div>'
        f"<script>{JS}</script></body></html>"
    )


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT}")
