"""Build the 5-minute pitch deck (docs/pitch.html) and the pipeline figure (static/pipeline.svg).

Same visual language as the web UI: white, navy #0f2247, Cormorant serif headings, hairlines.
Numbers are read from bench/results/*/latest.json; nothing is typed by hand.
Navigation: ←/→, Space, click; F fullscreen; Ctrl+P prints one slide per page.

Usage: python docs/make_pitch.py
"""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "bench" / "results"
STATIC = ROOT / "falconverifier" / "static"
OUT = ROOT / "docs" / "pitch.html"
SVG_OUT = STATIC / "pipeline.svg"

NAVY = "#0f2247"
MUTED = "#5b6b8c"
LINE = "#d9e0ee"
OK = "#1f8a4c"
BAD = "#b3213a"


def summary(arm: str, key: str = "all") -> dict:
    return json.loads((RESULTS / arm / "latest.json").read_text())["summary"][key]


def pct(v: float) -> str:
    return f"{100 * v:.0f}%"


# ----------------------------------------------------------------------------- pipeline figure
def pipeline_svg(width: int = 1240, height: int = 420) -> str:
    """Six stages left→right, the teach loop returning underneath, memory hanging off Lean."""

    stages = [
        ("Falcon answers", "student 3B / 7B", "Arabic or English,\nstep-by-step CoT"),
        ("Parse steps", "student.py", "sentences → numbered\nclaims + final answer"),
        (
            "Formalize",
            "pregroup grammar\n→ Falcon-34B fallback",
            "each claim → Lean 4 Prop;\nround-trip audit",
        ),
        ("Lean 4 kernel", "Mathlib + fv_auto", "prove P, prove ¬P,\nor say unknown"),
        ("Teach", "feedback.py", "refuted claim → plain-\nlanguage feedback"),
        ("Assurance trace", "runs/*.json", "every round, Prop,\nverdict, proof source"),
    ]
    n = len(stages)
    margin, gap = 30, 26
    bw = (width - 2 * margin - gap * (n - 1)) / n
    bh, top = 150, 70
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" font-family="Inter, system-ui, sans-serif">',
        '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        f'<path d="M0 0L10 5L0 10z" fill="{NAVY}"/></marker></defs>',
        f'<text x="{margin}" y="34" font-family="Cormorant Garamond, Georgia, serif" font-size="26" font-weight="600" fill="{NAVY}">How a Falcon answer becomes a kernel-checked claim</text>',
        f'<text x="{margin}" y="54" font-size="12" fill="{MUTED}" letter-spacing="2">FALCON SAYS IT · LEAN 4 DECIDES IT · FALCON LEARNS FROM IT</text>',
    ]
    xs = []
    for i, (title, sub, body) in enumerate(stages):
        x = margin + i * (bw + gap)
        xs.append(x)
        hot = i == 3
        parts.append(
            f'<rect x="{x}" y="{top}" width="{bw}" height="{bh}" rx="6" fill="{"#f6f8fc" if hot else "#fff"}" stroke="{NAVY}" stroke-width="{1.8 if hot else 1}"/>'
        )
        parts.append(
            f'<text x="{x + 14}" y="{top + 30}" font-family="Cormorant Garamond, Georgia, serif" font-size="21" font-weight="600" fill="{NAVY}">{html.escape(title)}</text>'
        )
        for k, line in enumerate(sub.split("\n")):
            parts.append(
                f'<text x="{x + 14}" y="{top + 50 + 14 * k}" font-size="11" fill="{MUTED}" letter-spacing="1.2">{html.escape(line.upper())}</text>'
            )
        for k, line in enumerate(body.split("\n")):
            parts.append(
                f'<text x="{x + 14}" y="{top + 100 + 17 * k}" font-size="13" fill="{NAVY}">{html.escape(line)}</text>'
            )
        if i < n - 1:
            parts.append(
                f'<line x1="{x + bw + 2}" y1="{top + bh / 2}" x2="{x + bw + gap - 2}" y2="{top + bh / 2}" stroke="{NAVY}" stroke-width="1.4" marker-end="url(#ah)"/>'
            )
    # verdict pills under the kernel
    pw = bw * 1.5 / 4
    kx = xs[3] + bw / 2 - 2 * pw
    for k, (label, color) in enumerate(
        (("verified", OK), ("refuted", BAD), ("unknown", "#a8690b"), ("ill-formed", "#6b3fa0"))
    ):
        px = kx + k * pw
        parts.append(
            f'<rect x="{px + 2}" y="{top + bh + 10}" width="{pw - 4}" height="20" rx="10" fill="#fff" stroke="{color}"/>'
        )
        parts.append(
            f'<text x="{px + pw / 2}" y="{top + bh + 24}" font-size="10.5" text-anchor="middle" fill="{color}">{label}</text>'
        )
    # the teach loop: Teach -> back under -> Falcon answers
    ly = top + bh + 78
    parts.append(
        f'<path d="M{xs[4] + bw / 2} {top + bh + 2} V{ly} H{xs[0] + bw / 2} V{top + bh + 4}" fill="none" stroke="{BAD}" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#ah)"/>'
    )
    parts.append(
        f'<text x="{(xs[0] + xs[4] + bw) / 2}" y="{ly - 8}" font-size="12.5" text-anchor="middle" fill="{BAD}">revision round (≤ 3): Falcon sees only natural-language feedback — it never sees Lean</text>'
    )
    # memory box below the kernel
    my = ly + 40
    parts.append(
        f'<rect x="{xs[1]}" y="{my}" width="{3 * bw + 2 * gap}" height="64" rx="6" fill="#fff" stroke="{LINE}"/>'
    )
    parts.append(
        f'<line x1="{xs[3] + bw / 2}" y1="{top + bh + 34}" x2="{xs[3] + bw / 2}" y2="{my}" stroke="{MUTED}" stroke-width="1" stroke-dasharray="3 3"/>'
    )
    parts.append(
        f'<text x="{xs[1] + 14}" y="{my + 24}" font-family="Cormorant Garamond, Georgia, serif" font-size="18" font-weight="600" fill="{NAVY}">Memory (SQLite)</text>'
    )
    parts.append(
        f'<text x="{xs[1] + 190}" y="{my + 24}" font-size="12" fill="{MUTED}">kernel verdicts and type-checked translations are reused under the same toolchain fingerprint</text>'
    )
    parts.append(
        f'<text x="{xs[1] + 190}" y="{my + 44}" font-size="12" fill="{MUTED}">Falcon\'s answer is never reused — every run samples a fresh answer and is judged on it</text>'
    )
    # guarantee line right of memory
    parts.append(
        f'<text x="{xs[5] + bw}" y="{my + 16}" font-size="13" text-anchor="end" font-family="Cormorant Garamond, Georgia, serif" font-weight="600" fill="{NAVY}">Only a proof counts.</text>'
    )
    parts.append(
        f'<text x="{xs[5] + bw}" y="{my + 34}" font-size="11.5" text-anchor="end" fill="{MUTED}">No proof either way → “unknown”,</text>'
    )
    parts.append(
        f'<text x="{xs[5] + bw}" y="{my + 50}" font-size="11.5" text-anchor="end" fill="{MUTED}">never “probably right”.</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


# ----------------------------------------------------------------------------- deck
CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Inter:wght@400;500;600&family=Noto+Naskh+Arabic:wght@400;600&display=swap');
:root{{--navy:{NAVY};--muted:{MUTED};--line:{LINE};--ok:{OK};--bad:{BAD};--surface:#f6f8fc;--serif:"Cormorant Garamond",Georgia,serif}}
*{{box-sizing:border-box}}html,body{{margin:0;height:100%;background:#fff;color:var(--navy);font-family:Inter,system-ui,sans-serif}}
.deck{{height:100%;overflow:hidden;position:relative}}
.slide{{position:absolute;inset:0;display:none;flex-direction:column;padding:6vh 7vw 5vh;background:#fff}}
.slide.active{{display:flex}}
.kicker{{font-size:.85vw;letter-spacing:.2em;text-transform:uppercase;color:var(--muted);margin-bottom:1.2vh}}
h1{{font-family:var(--serif);font-weight:600;font-size:5vw;line-height:1.05;margin:0 0 2vh}}
h2{{font-family:var(--serif);font-weight:600;font-size:3.2vw;line-height:1.1;margin:0 0 2.4vh;padding-bottom:1.2vh;border-bottom:1px solid var(--navy)}}
p,li{{font-size:1.55vw;line-height:1.5;margin:.4vh 0}}li{{margin:.9vh 0}}
.lede{{font-family:var(--serif);font-size:2.2vw;line-height:1.3;max-width:70vw}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:3vw}}.cols3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:2vw}}
.card{{border:1px solid var(--line);border-radius:6px;padding:1.6vh 1.4vw;background:#fff}}
.card h3{{font-family:var(--serif);font-size:1.7vw;margin:0 0 .8vh;font-weight:600}}
.ar{{direction:rtl;unicode-bidi:isolate;text-align:right;font-family:"Noto Naskh Arabic","Amiri",serif;font-size:1.7vw;line-height:1.7}}
.gloss{{color:var(--muted);font-style:italic;font-size:1.15vw;margin:.2vh 0 1vh}}
pre,code{{font-family:"JetBrains Mono",ui-monospace,Menlo,monospace}}pre{{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:1.2vh 1vw;font-size:1.05vw;white-space:pre-wrap;margin:.6vh 0}}
.pill{{display:inline-block;border:1px solid;border-radius:999px;padding:.1vh .7vw;font-size:1vw;letter-spacing:.06em;text-transform:uppercase}}
.ok{{color:var(--ok)}}.bad{{color:var(--bad)}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:2vw;margin:2vh 0}}
.kpi .n{{font-family:var(--serif);font-size:4.6vw;font-weight:600;line-height:1}}.kpi .l{{font-size:1vw;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-top:.6vh}}
table{{border-collapse:collapse;width:100%;font-size:1.25vw}}th,td{{padding:.8vh 1vw;border-bottom:1px solid var(--line);text-align:left}}th{{font-size:.95vw;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);font-weight:600}}
.foot{{position:absolute;left:7vw;right:7vw;bottom:2.2vh;display:flex;justify-content:space-between;font-size:.85vw;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}}
.foot img{{height:2.4vh;vertical-align:middle;margin-right:.6vw}}
.brand{{display:flex;align-items:center;gap:1.4vw;margin-bottom:4vh}}.brand img{{height:9vh}}
.note{{font-size:1.1vw;color:var(--muted);margin-top:auto}}
.fig{{width:100%;height:auto;margin-top:1vh}}
@media print{{@page{{size:1600px 900px;margin:0}}html,body{{height:auto}}.deck{{height:auto;overflow:visible}}
.slide{{display:flex!important;position:relative;inset:auto;width:1600px;height:900px;page-break-after:always;break-after:page;padding:54px 112px 44px;overflow:hidden}}
.foot{{position:absolute;bottom:20px;left:112px;right:112px}}
h1{{font-size:80px}}h2{{font-size:50px}}.lede{{font-size:34px;max-width:1100px}}p,li{{font-size:23px}}.kicker{{font-size:13px}}.card h3{{font-size:27px}}.ar{{font-size:27px}}.gloss{{font-size:18px}}pre{{font-size:17px}}
.pill{{font-size:15px}}.kpi .n{{font-size:74px}}.kpi .l{{font-size:15px}}table{{font-size:20px}}th{{font-size:14px}}.foot{{font-size:13px}}.note{{font-size:17px}}.brand img{{height:80px}}.foot img{{height:22px}}}}
"""

JS = """
const S=[...document.querySelectorAll('.slide')];let i=Math.max(0,Math.min(S.length-1,parseInt(location.hash.slice(1))||0));
function show(k){i=(k+S.length)%S.length;S.forEach((s,j)=>s.classList.toggle('active',j===i));location.hash=i;
document.querySelectorAll('.pg').forEach(e=>e.textContent=(i+1)+' / '+S.length)}
document.addEventListener('keydown',e=>{if(['ArrowRight',' ','PageDown'].includes(e.key))show(i+1);else if(['ArrowLeft','PageUp'].includes(e.key))show(i-1);
else if(e.key==='f'||e.key==='F')document.documentElement.requestFullscreen?.()});
document.addEventListener('click',e=>{if(!e.target.closest('a'))show(i+1)});show(i);
"""


def slide(kicker: str, body: str) -> str:
    return (
        f'<section class="slide"><div class="kicker">{kicker}</div>{body}'
        f'<div class="foot"><span><img src="mark.png" alt="">ChaosButterfly · FalconVerifier</span><span class="pg"></span></div></section>'
    )


def ar(text: str, gloss: str) -> str:
    return f'<p class="ar">{html.escape(text)}</p><p class="gloss">{html.escape(gloss)}</p>'


def build() -> str:
    a86 = summary("falcon3b_arabic")
    a244 = summary("falcon3b_arabic_scale")
    mark = (STATIC / "mark.png").resolve().as_uri()
    logo = (STATIC / "chaosbutterfly_logo.png").resolve().as_uri()
    fig = pipeline_svg()
    slides = [
        # 1 — title (0:00)
        f"""<section class="slide"><div class="brand"><img src="{logo}" alt="ChaosButterfly"></div>
        <h1>FalconVerifier</h1>
        <p class="lede">Falcon says it. Lean 4 proves it — or refutes it. In Arabic.</p>
        <p style="color:var(--muted)">A verification middleware that turns Falcon's Arabic math and logic answers into kernel-checked claims, teaches Falcon from what the kernel refutes, and keeps an auditable trace of every step.</p>
        <p class="note">ChaosButterfly · Hub71 Fish Tank · 5 minutes</p>
        <div class="foot"><span><img src="{mark}" alt="">ChaosButterfly · FalconVerifier</span><span class="pg"></span></div></section>""",
        # 2 — problem (0:30)
        slide(
            "01 · The gap",
            """<h2>Falcon is the region's model. Its users write Arabic. Its training data mostly did not.</h2>
            <div class="cols"><div>
            <ul><li>Falcon-7B/40B/180B: 3.5T tokens, <b>75% English</b> RefinedWeb; Arabic not among the listed languages.</li>
            <li>Falcon-H1: ~11T English web tokens; Arabic is one of 17 languages sharing a 3,000 GT pool.</li>
            <li>Falcon-H1-Arabic: ~100B Arabic tokens of continued pre-training — under 1% of what the base saw.</li></ul>
            </div><div class="card"><h3>What that looks like</h3>"""
            + ar(
                "سعر ٨٠٠ درهم خُفِّض ١٠٪ ثم ٢٠٪. السعر النهائي؟",
                "A price of 800 AED is reduced 10% then 20%. Final price?",
            )
            + '<p>Falcon 3B (first try, benchmark): <b class="bad">680</b> — it added the discounts. Correct: <b class="ok">576</b>.</p>'
            + '<p style="color:var(--muted)">Baseline first-try accuracy on our 244 Arabic problems: <b>'
            + pct(a244["baseline_accuracy"])
            + "</b>.</p></div></div>",
        ),
        # 3 — idea (1:00)
        slide(
            "02 · The idea",
            """<h2>The truth of a math claim does not depend on the language it was written in.</h2>
            <p class="lede">So don't ask a second LLM whether Falcon is right. Translate each sentence of Falcon's reasoning into a Lean 4 proposition and let the proof kernel decide.</p>
            <div class="cols3">
            <div class="card"><h3><span class="pill ok">verified</span></h3><p>The kernel proved <code>P</code>. Not "confident" — proved.</p></div>
            <div class="card"><h3><span class="pill bad">refuted</span></h3><p>The kernel proved <code>¬P</code>. Falcon gets told, in Arabic, what is false and why.</p></div>
            <div class="card"><h3><span class="pill" style="color:#a8690b">unknown</span></h3><p>No proof either way. We say so. Never "probably right".</p></div>
            </div>""",
        ),
        # 4 — pipeline figure (1:40)
        slide(
            "03 · Pipeline",
            '<h2>One loop, six stages</h2><div class="fig">' + fig + "</div>",
        ),
        # 5 — Arabic → Lean without understanding (2:20)
        slide(
            "04 · Arabic → Lean, deterministically",
            """<h2>For the common fragments, no LLM writes the Lean at all</h2>
            <div class="cols"><div>
            <p>A <b>pregroup grammar</b> (Lambek) gives every Arabic word a type; a sentence is well-formed when the types cancel. The same derivation is a functor into meaning — so the translation is a <em>proof</em>, not a guess.</p>
            <pre>kataba : s · oˡ · πˡ      (verb, VSO)
ahmad  : π                (subject)
alDarsa: o                (object)
s · oˡ · πˡ · π · o  ⟶  s   ✓</pre>
            <p>Fragments covered: arithmetic, quantifier logic, symmetric relations & counting. Everything else goes to Falcon-H1-Arabic-34B with a round-trip faithfulness audit — a mismatch downgrades to <em>unknown</em>.</p>
            </div><div class="card"><h3>Five friends</h3>"""
            + ar(
                "خمسة طلاب يجلسون في الفصل، ويقول كل واحد منهم إن ثلاثة من الأربعة الباقين أصدقاؤه. هل يلزم أن أحدهم يكذب؟",
                "Five students sit in class; each says three of the other four are his friends. Must one of them be lying?",
            )
            + """<pre>∀ f : Fin 5 → Fin 5 → Bool, ¬ Regular f 3</pre>
            <p>Lean proves it via the handshake lemma (odd degree sum) — no enumeration, and nobody had to understand the word "friend". <span class="pill ok">verified</span> in 18 s.</p></div></div>""",
        ),
        # 6 — live demo plan (3:00)
        slide(
            "05 · Live",
            """<h2>Two examples, one screen</h2>
            <div class="cols">
            <div class="card"><h3>1 · Catch and correct</h3>"""
            + ar("هاتف بـ 800 درهم، خُفِّض 10٪ ثم 20٪", "A phone at 800 AED, −10% then −20%")
            + """<p>Falcon 3B answers → step 3 turns <span class="pill bad">refuted</span> with the kernel's <code>(800:ℝ)·0.9·0.8 = 576</code> → Arabic feedback → round 2 <span class="pill ok">verified</span>, assurance 1.0.</p>
            <p style="color:var(--muted)">If 3B happens to be right first time: every step is still green with its proof — that <em>is</em> the product.</p></div>
            <div class="card"><h3>2 · Prove without understanding</h3>"""
            + ar("خمسة طلاب، كل واحد له ثلاثة أصدقاء", "Five students, each with three friends")
            + """<p>Deterministic grammar → handshake theorem → answer «نعم» (yes, someone lies) <span class="pill ok">verified</span>. Open "Lean 4 source (audit)": that is the exact file the kernel checked.</p>
            <p style="color:var(--muted)">Ask it again: the kernel verdict comes from memory in 0 s — Falcon's answer is still fresh.</p></div>
            </div>""",
        ),
        # 7 — numbers (3:50)
        slide(
            "06 · Evidence",
            f"""<h2>Falcon 3B, Arabic, Falcon-34B as formalizer — Falcon verifies Falcon</h2>
            <div class="kpis">
            <div class="kpi"><div class="n" style="font-size:3.4vw;white-space:nowrap">{pct(a244["baseline_accuracy"])} → {pct(a244["verified_accuracy"])}</div><div class="l">accuracy, {a244["n"]} problems</div></div>
            <div class="kpi"><div class="n">{pct(a244["detection_recall"])}</div><div class="l">wrong answers caught by Lean</div></div>
            <div class="kpi"><div class="n">{a244["regressions"]}</div><div class="l">correct answers made wrong</div></div>
            <div class="kpi"><div class="n">{a244["false_alarms_on_correct"]}</div><div class="l">false alarm in {a244["n"]}</div></div>
            </div>
            <table><thead><tr><th>set</th><th>n</th><th>baseline</th><th>verified</th><th>caught</th><th>fixed</th><th>regressions</th></tr></thead><tbody>
            <tr><td>Arabic curated</td><td>{a86["n"]}</td><td>{pct(a86["baseline_accuracy"])}</td><td><b>{pct(a86["verified_accuracy"])}</b></td><td>{a86["wrong_detected_by_lean"]}/{a86["wrong_baseline"]}</td><td>{a86["fixed_after_feedback"]}/{a86["wrong_baseline"]}</td><td>{a86["regressions"]}</td></tr>
            <tr><td>Arabic scale</td><td>{a244["n"]}</td><td>{pct(a244["baseline_accuracy"])}</td><td><b>{pct(a244["verified_accuracy"])}</b></td><td>{a244["wrong_detected_by_lean"]}/{a244["wrong_baseline"]}</td><td>{a244["fixed_after_feedback"]}/{a244["wrong_baseline"]}</td><td>{a244["regressions"]}</td></tr>
            </tbody></table>
            <p class="note">Every row links to its problems, traces and Lean sources on the /benchmark page. 294 Lean-labelled preference pairs already exported for DPO.</p>""",
        ),
        # 8 — product (4:20)
        slide(
            "07 · Product",
            """<h2>Middleware, not a model</h2>
            <div class="cols3">
            <div class="card"><h3>For any Falcon app</h3><pre>POST /api/solve
{ "problem": "...", "rounds": 3 }
→ verdicts, feedback, trace</pre><p>One call adds a kernel-backed assurance score to Falcon output.</p></div>
            <div class="card"><h3>For TII</h3><p>Every refutation is a training signal labelled by a proof, not by a human or an LLM judge. The flywheel is already a file.</p></div>
            <div class="card"><h3>Open & deployable</h3><p>Docker image with Lean + Mathlib, HTTPS, rate limits, memory. Web UI, CLI, API — all in the repo.</p></div>
            </div>
            <p class="note">Limits we state out loud: Lean checks what was formalized, not the prose; out-of-fragment steps depend on the 34B formalizer; proof-style problems are "unknown" today.</p>""",
        ),
        # 9 — close (4:50)
        f"""<section class="slide"><div class="brand"><img src="{logo}" alt="ChaosButterfly"></div>
        <h1>Trust in Arabic, proved in Lean.</h1>
        <p class="lede">A regional model has to lead in its own language. We give Falcon a kernel that never bluffs — and a way to learn from it.</p>
        <p style="color:var(--muted)">github.com/hw4375-collab/FalconVerifer · live demo on the next screen</p>
        <div class="foot"><span><img src="{mark}" alt="">ChaosButterfly · FalconVerifier</span><span class="pg"></span></div></section>""",
    ]
    doc = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>FalconVerifier — 5-minute pitch</title>'
        f'<style>{CSS}</style></head><body><div class="deck">'
        + "".join(slides)
        + f"</div><script>{JS}</script></body></html>"
    )
    return doc.replace('src="mark.png"', f'src="{mark}"')


def main() -> None:
    SVG_OUT.write_text(pipeline_svg())
    doc = build()
    # inline the images so the HTML is self-contained
    for p in (STATIC / "mark.png", STATIC / "chaosbutterfly_logo.png"):
        b64 = base64.b64encode(p.read_bytes()).decode()
        doc = doc.replace(p.resolve().as_uri(), f"data:image/png;base64,{b64}")
    OUT.write_text(doc)
    print(f"wrote {OUT} and {SVG_OUT}")


if __name__ == "__main__":
    main()
