"""Build docs/slides.html (self-contained pitch deck) from the latest benchmark results.

Usage: python docs/make_slides.py
Navigate with ←/→, Space, or click; press F for fullscreen, O for overview.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "bench" / "results"
OUT = ROOT / "docs" / "slides.html"

ARM_LABELS = {
    "falcon_formalizer": "Standard set · Falcon 7B",
    "falcon_formalizer_hard": "Hard set · Falcon 7B",
    "falcon3b_formalizer_hard": "Hard set · Falcon 3B",
    "falcon3b_formalizer": "Standard set · Falcon 3B",
    "falcon3b_v2": "Math slice · Falcon 3B · v2 guards",
    "falcon7b_arabic": "Arabic set · Falcon 7B",
    "falcon3b_arabic": "Arabic set · Falcon 3B",
    "openai_formalizer": "Standard set · GPT formalizer",
}


def arabic_slice(arms: dict[str, dict]) -> str:
    present = [(k, arms[k]) for k in ("falcon7b_arabic", "falcon3b_arabic") if k in arms]
    if not present:
        return '<p class="note">Arabic benchmark: run <code>falconverifier bench --dataset bench/problems_ar.jsonl</code>.</p>'
    rows = []
    for name, d in present:
        model = "7B" if "7b" in name else "3B"
        for key, label in (
            ("all", "all"),
            ("math", "math"),
            ("logic", "logic"),
            ("fragment", "pregroup fragment"),
            ("eastern-digits", "Eastern digits ٠-٩"),
        ):
            s = d["summary"].get(key)
            if not s:
                continue
            rows.append(
                f"<tr><th>{model}</th><th>{label}</th><td>{s['n']}</td><td>{pct(s['baseline_accuracy'])}</td>"
                f"<td><b>{pct(s['verified_accuracy'])}</b></td><td>{s['wrong_detected_by_lean']}/{s['wrong_baseline']}</td>"
                f"<td>{s['fixed_after_feedback']}/{s['wrong_baseline']}</td><td>{s['false_alarms_on_correct']}</td><td>{s['regressions']}</td></tr>"
            )
    return (
        '<table class="kpi"><thead><tr><th>Falcon</th><th>slice</th><th>n</th><th>baseline</th><th>verified</th>'
        "<th>caught</th><th>fixed</th><th>false alarms</th><th>regr.</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def latest() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if RESULTS.exists():
        for sub in sorted(RESULTS.iterdir()):
            runs = sorted(sub.glob("run_*/results.json"))
            if runs:
                out[sub.name] = json.loads(runs[-1].read_text())
    return out


def pct(v) -> str:
    return "–" if v is None else f"{100 * v:.0f}%"


def bars(arms: dict[str, dict]) -> str:
    rows = []
    for name, d in arms.items():
        for s in ("math", "logic"):
            if s in d["summary"]:
                sm = d["summary"][s]
                rows.append(
                    (
                        f"{ARM_LABELS.get(name, name)} — {s}",
                        sm["baseline_accuracy"],
                        sm["verified_accuracy"],
                        sm["n"],
                    )
                )
    out = ['<div class="bars">']
    for label, b, v, n in rows:
        out.append(
            f'<div class="bar-row"><div class="bar-label">{html.escape(label)} <span class="dim">(n={n})</span></div>'
            f'<div class="bar-track"><div class="bar base" style="width:{100 * b:.1f}%"><span>{pct(b)}</span></div></div>'
            f'<div class="bar-track"><div class="bar ver" style="width:{100 * v:.1f}%"><span>{pct(v)}</span></div></div></div>'
        )
    out.append(
        '<div class="legend"><span class="sw base"></span>Falcon baseline&nbsp;&nbsp;<span class="sw ver"></span>Falcon + Lean verifier</div></div>'
    )
    return "\n".join(out)


def table(arms: dict[str, dict]) -> str:
    keys = [
        ("n", "problems", str),
        ("baseline_accuracy", "baseline", pct),
        ("verified_accuracy", "with verifier", pct),
        ("wrong_baseline", "wrong at baseline", str),
        ("wrong_detected_by_lean", "caught by Lean", str),
        ("fixed_after_feedback", "fixed by feedback", str),
        ("answers_with_refuted_claims_r1", "answers w/ refuted step", str),
        ("false_alarm_rate", "false-alarm rate", pct),
        ("regressions", "regressions", str),
        ("mean_latency_s", "latency (s)", str),
    ]
    head = "".join(f"<th>{html.escape(ARM_LABELS.get(n, n))}</th>" for n in arms)
    body = []
    for k, label, f in keys:
        cells = "".join(f"<td>{f(d['summary']['all'].get(k))}</td>" for d in arms.values())
        body.append(f"<tr><th>{label}</th>{cells}</tr>")
    return f'<table class="kpi"><thead><tr><th></th>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def totals(arms: dict[str, dict]) -> dict[str, int]:
    t = {"n": 0, "wrong": 0, "caught": 0, "fixed": 0, "reg": 0, "halluc": 0}
    for d in arms.values():
        s = d["summary"]["all"]
        t["n"] += s["n"]
        t["wrong"] += s["wrong_baseline"]
        t["caught"] += s["wrong_detected_by_lean"]
        t["fixed"] += s["fixed_after_feedback"]
        t["reg"] += s["regressions"]
        t["halluc"] += s["answers_with_refuted_claims_r1"]
    return t


CSS = """
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#070b14;color:#e6edf3;font-family:Inter,"Segoe UI",system-ui,sans-serif}
.deck{height:100%;overflow:hidden;position:relative}
.slide{position:absolute;inset:0;display:none;flex-direction:column;justify-content:center;padding:6vh 8vw;background:radial-gradient(1200px 600px at 80% -10%,#12233f 0%,#070b14 60%)}
.slide.active{display:flex}
h1{font-size:5.2vw;line-height:1.05;margin:0 0 2vh;font-weight:800;letter-spacing:-.02em}
h2{font-size:3.2vw;margin:0 0 3vh;font-weight:750;letter-spacing:-.01em}
h2 small{display:block;font-size:1.3vw;color:#8b9bb4;font-weight:500;margin-top:.6vh}
p,li{font-size:1.75vw;line-height:1.45}li{margin:.7vh 0}
.sub{color:#9fb0c8;font-size:2.2vw}
.tag{display:inline-block;background:#1e3a8a;color:#bfdbfe;padding:.3em .8em;border-radius:999px;font-size:1.2vw;margin-bottom:2vh;font-weight:600}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:4vw;align-items:start}
.card{background:#0e1626;border:1px solid #1f2b44;border-radius:14px;padding:2.2vh 2vw}
.card h3{margin:0 0 1vh;font-size:1.6vw;color:#93c5fd}
code,pre{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace}
pre{background:#050810;border:1px solid #1f2b44;border-radius:10px;padding:1.6vh 1.4vw;font-size:1.25vw;line-height:1.45;overflow:hidden;margin:0}
.flow{display:flex;align-items:center;gap:1.2vw;flex-wrap:wrap;margin:2vh 0}
.node{background:#0e1626;border:1px solid #2b3d63;border-radius:12px;padding:1.4vh 1.4vw;font-size:1.35vw;min-width:9vw;text-align:center}
.node b{display:block;color:#93c5fd;font-size:1.2vw;margin-bottom:.3vh}
.node.lean{border-color:#22c55e;box-shadow:0 0 0 2px #22c55e33}
.arrow{color:#5b6b8a;font-size:2.2vw}
.v{display:inline-block;padding:.15em .6em;border-radius:6px;font-weight:700;font-size:1.3vw}
.v.ok{background:#14532d;color:#86efac}.v.bad{background:#7f1d1d;color:#fecaca}.v.unk{background:#3f3f46;color:#e4e4e7}.v.ill{background:#78350f;color:#fde68a}
table.kpi{border-collapse:collapse;width:100%;font-size:1.45vw}
table.kpi th,table.kpi td{padding:.9vh 1vw;border-bottom:1px solid #1f2b44;text-align:right}
table.kpi th:first-child{text-align:left;color:#9fb0c8;font-weight:500}table.kpi thead th{color:#93c5fd;font-weight:700}
.bars{display:flex;flex-direction:column;gap:1.4vh;margin-top:1vh}
.bar-row{display:grid;grid-template-columns:22vw 1fr;grid-template-rows:auto auto;column-gap:1.5vw;row-gap:.5vh;align-items:center}
.bar-label{grid-row:1/3;font-size:1.35vw}.dim{color:#7f8ea8}
.bar-track{background:#111b2e;border-radius:6px;height:2.4vh;position:relative}
.bar{height:100%;border-radius:6px;position:relative}.bar.base{background:#64748b}.bar.ver{background:#22c55e}
.bar span{position:absolute;right:.6vw;top:0;line-height:2.4vh;font-size:1.1vw;font-weight:700;color:#06111f}
.legend{font-size:1.2vw;color:#9fb0c8;margin-top:1vh}.sw{display:inline-block;width:1vw;height:1vw;border-radius:3px;margin-right:.4vw;vertical-align:middle}
.sw.base{background:#64748b}.sw.ver{background:#22c55e}
.big{display:flex;gap:3vw;margin:2vh 0}.big div{flex:1}.big .n{font-size:5vw;font-weight:800;color:#86efac;line-height:1}.big .l{color:#9fb0c8;font-size:1.3vw;margin-top:.6vh}
.foot{position:absolute;bottom:2.5vh;left:8vw;right:8vw;display:flex;justify-content:space-between;color:#5b6b8a;font-size:1.1vw}
.note{font-size:1.25vw;color:#8b9bb4;margin-top:2vh}
.overview .slide{display:flex!important;position:relative;inset:auto;transform:scale(.24);transform-origin:top left;width:100vw;height:100vh;margin:-38vh -38vw 0 0;border:1px solid #334;cursor:pointer}
.overview{display:grid;grid-template-columns:repeat(4,24vw);grid-auto-rows:24vh;gap:1vw;padding:1vw;overflow:auto;height:100%}
"""

JS = """
const S=[...document.querySelectorAll('.slide')];let i=Math.max(0,Math.min(S.length-1,+location.hash.slice(1)||0));
function show(k){S.forEach((s,j)=>s.classList.toggle('active',j===k));i=k;location.hash=k;document.getElementById('pg').textContent=(k+1)+' / '+S.length;}
document.addEventListener('keydown',e=>{if(e.key==='ArrowRight'||e.key===' '||e.key==='PageDown')show(Math.min(i+1,S.length-1));
else if(e.key==='ArrowLeft'||e.key==='PageUp')show(Math.max(i-1,0));else if(e.key==='Home')show(0);else if(e.key==='End')show(S.length-1);
else if(e.key==='f'||e.key==='F'){document.documentElement.requestFullscreen?.()}
else if(e.key==='o'||e.key==='O'){document.querySelector('.deck').classList.toggle('overview')}});
document.querySelector('.deck').addEventListener('click',e=>{const d=document.querySelector('.deck');
if(d.classList.contains('overview')){const s=e.target.closest('.slide');if(s){d.classList.remove('overview');show(S.indexOf(s))}}
else if(!e.target.closest('a'))show(Math.min(i+1,S.length-1))});show(i);
"""


def slide(body: str, cls: str = "") -> str:
    return f'<section class="slide {cls}">{body}</section>'


def build() -> str:
    arms = latest()
    t = totals(arms)
    demo_url = "http://localhost:8000"
    slides = [
        slide(
            '<span class="tag">Hub71 Hackathon · Abu Dhabi</span>'
            "<h1>FalconVerifier</h1>"
            '<p class="sub">Lean 4 as a truth oracle for Falcon — every reasoning step is a theorem, '
            "every hallucination is a refuted theorem, and Falcon is <em>taught</em> from the proof.</p>"
            '<p class="note">Falcon-H1-7B-Instruct · Falcon-H1-34B formalizer · Lean 4 + Mathlib · open source</p>'
        ),
        slide(
            "<h2>The problem<small>Small models are cheap and fast — and confidently wrong</small></h2>"
            '<div class="cols"><div>'
            "<ul><li>A 7B model's chain of thought <b>looks</b> rigorous, but a single wrong intermediate step "
            "silently poisons the answer.</li>"
            "<li>Today's fix is <b>LLM-as-judge</b>: asking another model whether the first one is right. "
            "That is circular — the judge hallucinates too.</li>"
            "<li>Regulated users (finance, education, government) need <b>evidence</b>, not a vibe.</li></ul>"
            '</div><div class="card"><h3>What Falcon 7B actually wrote (benchmark trace)</h3>'
            '<pre>Step 2: 50% of 150 = 75\nStep 4: 150 + 75 = 225\n…\nStep 3: 340 + 51 = <b style="color:#fca5a5">381</b>  ← wrong\nFINAL ANSWER: 381</pre>'
            '<p class="note">Fluent, numbered, and false. No LLM judge reliably flags the third line; Lean proves ¬(340 + 51 = 381) in milliseconds.</p></div></div>'
        ),
        slide(
            "<h2>The idea<small>Don't ask an LLM if Falcon is right. Ask the Lean kernel.</small></h2>"
            '<div class="flow">'
            '<div class="node"><b>user</b>problem</div><span class="arrow">→</span>'
            '<div class="node"><b>Falcon 7B</b>steps + answer</div><span class="arrow">→</span>'
            '<div class="node"><b>formalizer</b>NL → Lean 4 Prop</div><span class="arrow">→</span>'
            '<div class="node lean"><b>Lean 4 + Mathlib</b>prove P / prove ¬P</div><span class="arrow">→</span>'
            '<div class="node"><b>teacher</b>what Lean refuted</div><span class="arrow">↺</span>'
            '<div class="node"><b>Falcon 7B</b>revises</div></div>'
            "<ul><li>Each reasoning step becomes a <b>closed Lean proposition</b>; one compilation checks them all.</li>"
            "<li>Lean tries to prove <code>P</code> <em>and</em> <code>¬P</code> with a tactic cascade "
            "(<code>decide norm_num omega simp tauto linarith nlinarith aesop …</code>).</li>"
            "<li>Only a <b>machine-proved refutation</b> becomes feedback. Falcon revises inside the same conversation.</li>"
            "<li>Every run leaves an <b>assurance trace</b>: what Falcon said, what Lean proved, what was taught.</li></ul>"
        ),
        slide(
            "<h2>Verification semantics<small>Honest verdicts — Lean's failure is never blamed on Falcon</small></h2>"
            '<div class="cols"><div>'
            "<pre>theorem s3_wf  : P := by sorry     -- type-checks?\n"
            "theorem s3_pos : P := by fv_auto   -- provable?\n"
            "theorem s3_neg : ¬P := by fv_auto  -- refutable?</pre>"
            '<table class="kpi" style="margin-top:2vh"><thead><tr><th>pos</th><th>neg</th><th>verdict</th></tr></thead><tbody>'
            '<tr><th>✓</th><td>✗</td><td><span class="v ok">verified</span></td></tr>'
            '<tr><th>✗</th><td>✓</td><td><span class="v bad">refuted</span> → strong feedback</td></tr>'
            '<tr><th>✗</th><td>✗</td><td><span class="v unk">unknown</span> → soft hint</td></tr>'
            '<tr><th colspan=2>type error</th><td><span class="v ill">ill-formed</span> → repair, then soft hint</td></tr>'
            "</tbody></table></div>"
            '<div><div class="card"><h3>Safety valves against false alarms</h3>'
            "<ul><li><b>ℚ-lift recheck</b> — <code>(50:ℕ)/100·150 = 75</code> is false in ℕ (truncation) but true in ℚ; "
            "refutations that vanish over ℚ are retracted deterministically.</li>"
            "<li><b>Literal grounding</b> — a refuted prop built only from numbers Falcon itself wrote needs no LLM opinion.</li>"
            "<li><b>Faithfulness audit</b> — otherwise the formalizer re-reads NL step vs. Lean prop (polarity, numbers); "
            "unfaithful → downgraded to <em>unknown</em>.</li>"
            "<li><b>Final-answer consistency</b> — Lean verified the derivation but <code>FINAL ANSWER</code> states a different number → refuted.</li></ul></div>"
            '<p class="note">Result: <b>zero regressions</b> across all benchmark arms — the verifier never turned a right answer wrong.</p></div></div>'
        ),
        slide(
            "<h2>Live demo<small>Falcon reasons · Lean judges · Falcon learns</small></h2>"
            '<div class="cols"><div class="card"><h3>1 · Happy path</h3><p>Word problem → every step turns '
            '<span class="v ok">verified</span>, final answer proved, assurance 1.0.</p></div>'
            '<div class="card"><h3>2 · The catch</h3><p>Fallacy / arithmetic slip → a step is '
            '<span class="v bad">refuted</span>; the feedback card quotes the step and the proposition Lean disproved; '
            "round 2 comes back green.</p></div></div>"
            f'<p class="note" style="margin-top:4vh">Web UI: <code>falconverifier serve</code> → {demo_url} · CLI: <code>falconverifier solve "…"</code> · '
            "Streaming SSE shows each stage as it happens.</p>"
        ),
        slide(
            "<h2>Evidence<small>Same problems, same Falcon 7B, with and without the Lean loop</small></h2>"
            + bars(arms)
            + '<p class="note">Datasets: generated basic-math word problems with exact answers + hand-written logic items '
            "(syllogisms, propositional fallacies, quantifier swaps, ordering, divisibility). Hard tier adds 3×3-digit products, compound "
            "percentages, order of operations, only-if/unless, 5-entity orderings.</p>"
        ),
        slide(
            "<h2>Evidence, in numbers</h2>"
            + table(arms)
            + '<p class="note">"Answers w/ refuted step" counts first-round answers containing at least one step Lean proved false — '
            "hallucinated reasoning that is invisible if you only grade the final answer.</p>"
        ),
        slide(
            "<h2>What the numbers say</h2>"
            f'<div class="big"><div><div class="n">{t["n"]}</div><div class="l">problems, {len(arms)} benchmark arms</div></div>'
            f'<div><div class="n">{t["caught"]}/{t["wrong"]}</div><div class="l">wrong baseline answers caught by Lean</div></div>'
            f'<div><div class="n">{t["fixed"]}/{t["wrong"]}</div><div class="l">fixed after one teaching round</div></div>'
            f'<div><div class="n">{t["reg"]}</div><div class="l">regressions (right → wrong)</div></div></div>'
            "<ul><li>Falcon 7B is already strong on grade-school arithmetic; the verifier's value shows up exactly where it fails — "
            "and in the <b>{h}</b> first-round answers whose reasoning contained a machine-refuted step.</li>"
            "<li>Every gain is <b>auditable</b>: the trace holds the Lean source and the proof outcome for each claim.</li>"
            "<li>Cost: ~25–30 s per problem end-to-end (two Falcon calls + one Lean compile); Lean itself is &lt;5 s.</li></ul>".format(
                h=t["halluc"]
            )
        ),
        slide(
            "<h2>Why this is a Falcon / UAE story</h2>"
            "<ul><li><b>Falcon verifies Falcon</b> — student <em>and</em> formalizer are Falcon-H1 models; no dependency on foreign frontier APIs "
            "(GPT is an optional comparison arm).</li>"
            "<li><b>Sovereign, on-prem capable</b> — any OpenAI-compatible endpoint (TII cloud, vLLM); Lean runs locally; nothing leaves the perimeter.</li>"
            "<li><b>A data flywheel for TII</b> — every refuted step is a labelled (wrong reasoning, proof of wrongness, corrected reasoning) triple: "
            "training data for RL-from-Lean-feedback on the next Falcon.</li>"
            "<li><b>Assurance artefact</b> — the trace is what education, finance and government buyers need to deploy a 7B model.</li></ul>"
        ),
        slide(
            "<h2>Arabic: why formal verification matters <em>more</em><small>Rich morphology, free word order, two digit systems — the NL→formal step is the fragile one</small></h2>"
            '<div class="cols"><div><ul>'
            "<li><b>VSO and SVO both grammatical</b> — «كتب أحمد الدرس» ≡ «أحمد كتب الدرس»; position is not a reliable cue for who-did-what.</li>"
            "<li><b>Meaning lives in morphology</b> — the verb carries person/gender/number of its subject; pro-drop puts the subject <em>inside</em> the verb («كتبوا الدرس»).</li>"
            "<li><b>Unwritten vowels &amp; case</b> — nominative/accusative endings that disambiguate subject from object are invisible on the page.</li>"
            "<li><b>٠١٢٣٤٥٦٧٨٩ · ٫ · ٬ · ٪</b> — two digit systems and their own separators; «٣٫٥» vs «3,5» silently changes the number.</li>"
            "<li><b>Small model, low-resource language</b> — more baseline errors, so more for an independent oracle to catch.</li></ul></div>"
            '<div class="card"><h3>Our answer</h3><ul>'
            "<li>A <b>pregroup grammar</b> (Lambek; Bargelli–Lambek for Arabic) translates the arithmetic fragment to Lean <b>deterministically</b>, with a derivation certificate — no LLM in the loop.</li>"
            "<li>A <b>quantifier fragment</b> («كل / بعض / لا أحد / إذا … فإن / إما … أو») → closed statements over finite Boolean models: Lean <em>decides</em> every syllogism, both ways, and the certificate records each lemma identification («مستطيلات ≡ المستطيلات»).</li>"
            "<li>Everything else falls back to an Arabic-aware LLM formalizer + the same guards.</li>"
            "<li>Lean 4 remains the only judge; feedback to Falcon is written in Arabic.</li></ul></div></div>"
        ),
        slide(
            "<h2>Pregroup syntax → typed meaning → Lean<small>The reduction is a proof; we store it in every trace</small></h2>"
            '<div class="cols"><div>'
            "<pre>«ما هو ناتج ١٧ × ٢٣؟»  +  FINAL ANSWER 391\n\n"
            "ما هو : q nˡ     ناتج : n nˡ     ١٧ : n\n× : nʳ n nˡ     ٢٣ : n\n\n"
            "q nˡ · n nˡ · n · nʳ n nˡ · n  →  q      (planar links)\n\n"
            '<b style="color:#86efac">(17:ℚ) * 23 = 391</b>   → Lean: verified</pre>'
            '<p class="note">Greedy left-to-right contraction gets this wrong (links «ناتج» to ١٧); the parser does the O(n³) planar matching, so the head scopes over the whole product.</p></div>'
            '<div class="card"><h3>Word order, proved equivalent (Lean)</h3>'
            "<pre>def kataba    := s₀ * oˡ * πˡ   -- VSO\ndef katabaSVO := πʳ * s₀ * oˡ   -- SVO\n"
            "theorem vso_valid : Derivable (kataba*ahmad*alDarsa) s₀\ntheorem svo_valid : Derivable (ahmad*katabaSVO*alDarsa) s₀\n"
            "theorem vso_svo_same_meaning :\n  meaningVSO v a b ↔ meaningSVO v a b := Iff.rfl</pre>"
            '<p class="note">Any order Falcon writes the claim in yields the same Lean proposition — and the derivation says why.</p></div></div>'
        ),
        slide(
            "<h2>Where pregroups lose faithfulness — and the fix, as theorems<small>Coarse types accept agreement violations; feature-indexed types reject them</small></h2>"
            '<div class="cols"><div class="card"><h3>Loss</h3>'
            "<pre>-- كتبتْ (fem.) + أحمد (masc.): ungrammatical Arabic\n"
            "theorem coarse_accepts_bad_agreement :\n  Derivable (katabatCoarse * ahmad * alDarsa) s₀</pre>"
            '<p class="note">One atom π for every subject: the morphology\'s “these words are not about the same referent” is erased.</p></div>'
            '<div class="card"><h3>Remedy</h3>'
            "<pre>-- atoms indexed by gender: πm, πf\ntheorem weight_preserved (w) (d : X ⊢ Y) :\n  weight w X = weight w Y      -- derivation invariant\n"
            "theorem indexed_rejects_bad_agreement :\n  ¬ Derivable (katabatF * ahmadF * alDarsaF) fs₀</pre>"
            '<p class="note">Not “we failed to find a derivation” — a proof that none exists. The Python lexicon mirrors it: «العدد ١٢ <b>ت</b>ساوي ٣» is rejected.</p></div></div>'
            '<p class="note">Research direction: feature-indexed atoms as dependent types; Lambek calculus with modalities for pro-drop/clitics; VSO≡SVO as a 2-cell between derivations (bicategorical semantics).</p>'
        ),
        slide(
            "<h2>Arabic evidence<small>76 Arabic problems (52 math, 24 logic), half with Eastern digits · Falcon 7B and 3B (Arabic-instruct)</small></h2>"
            + arabic_slice(arms)
            + '<p class="note">“pregroup fragment” = bare arithmetic questions translated with zero LLM calls in the formalizer. '
            "Same grading as the English arms: exact answer match, «نعم»/«لا» for logic. Logic questions: 16/24 are inside the deterministic quantifier fragment (decided by Lean in both polarities, 0 false alarms); "
            "for the rest the yes/no polarity is fixed mechanically and a degeneracy filter plus an LLM faithfulness audit gate every refutation.</p>"
        ),
        slide(
            "<h2>Roadmap</h2>"
            '<div class="cols"><div class="card"><h3>Next 4 weeks</h3><ul>'
            "<li>Fine-tune a Falcon formalizer on the assurance traces (ill-formed rate ↓, coverage ↑).</li>"
            "<li>Grow the Arabic fragments: full verb paradigms, relative clauses («الذي/التي»), numerals inside quantified atoms.</li>"
            "<li>Lean server mode: persistent Mathlib env, &lt;1 s per check.</li></ul></div>"
            '<div class="card"><h3>Next quarter</h3><ul>'
            "<li>Domains beyond arithmetic/logic: units &amp; finance formulas, set/graph puzzles, program invariants.</li>"
            "<li>RL from Lean feedback: refuted → corrected pairs as preference data for Falcon.</li>"
            "<li>Chrome/IDE/chat plug-in: the verifier as a layer on any Falcon conversation.</li></ul></div></div>"
        ),
        slide(
            "<h1>Ask the kernel, not the model.</h1>"
            '<p class="sub">github.com/hw4375-collab/FalconVerifer · MIT · <code>pip install -e . &amp;&amp; falconverifier serve</code></p>'
            '<p class="note">Built in one night with Falcon-H1 + Lean 4 + Mathlib. Thank you.</p>'
        ),
    ]
    body = "\n".join(slides)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>FalconVerifier — Hub71 pitch</title>'
        f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head><body>'
        f'<div class="deck">{body}<div class="foot"><span>FalconVerifier · Lean 4 as a truth oracle for Falcon</span><span id="pg"></span></div></div>'
        f"<script>{JS}</script></body></html>"
    )


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT}")
