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
import math
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
.fig{{width:100%;height:auto;max-height:66vh;margin-top:1vh}}
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


def _svg(w: int, h: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" class="fig" font-family="Inter, system-ui, sans-serif">'
        '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        f'<path d="M0 0L10 5L0 10z" fill="{NAVY}"/></marker>'
        '<marker id="ahr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        f'<path d="M0 0L10 5L0 10z" fill="{BAD}"/></marker></defs>{body}</svg>'
    )


def _t(x, y, text, size=14, fill=NAVY, anchor="start", weight=400, serif=False, extra=""):
    ff = ' font-family="Cormorant Garamond, Georgia, serif"' if serif else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}"{ff} {extra}>{html.escape(str(text))}</text>'


def _arrow(x1, y1, x2, y2, color=NAVY, dash="", marker="ah"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6"{d} marker-end="url(#{marker})"/>'


def _box(x, y, w, h, title, sub="", fill="#fff", stroke=NAVY, sw=1):
    out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    out += _t(
        x + w / 2,
        y + h / 2 + (2 if not sub else -4),
        title,
        20,
        anchor="middle",
        weight=600,
        serif=True,
    )
    if sub:
        out += _t(x + w / 2, y + h / 2 + 16, sub, 11.5, MUTED, "middle")
    return out


def gap_svg(baseline: float) -> str:
    """Language share of Falcon training data → first-try Arabic accuracy."""
    rows = [
        ("Falcon 7B–180B · RefinedWeb", 0.75, 0.0, "75% English · Arabic not listed"),
        ("Falcon-H1 · ~18T tokens", 0.61, 0.02, "~11T English · Arabic ⊂ 17-language pool"),
        ("Falcon-H1-Arabic · +300B", 0.33, 0.33, "~100B Arabic ≈ <1% of what the base saw"),
    ]
    b = []
    x0, bw = 40, 620
    for i, (label, en, ar_, note) in enumerate(rows):
        y = 40 + i * 80
        b.append(_t(x0, y - 8, label, 13, MUTED))
        b.append(
            f'<rect x="{x0}" y="{y}" width="{bw}" height="26" fill="#f6f8fc" stroke="{LINE}"/>'
        )
        b.append(f'<rect x="{x0}" y="{y}" width="{bw * en}" height="26" fill="{NAVY}"/>')
        b.append(f'<rect x="{x0 + bw * en}" y="{y}" width="{bw * ar_}" height="26" fill="{OK}"/>')
        b.append(_t(x0 + 8, y + 18, "English", 12, "#fff"))
        if ar_ > 0.05:
            b.append(_t(x0 + bw * en + 8, y + 18, "Arabic", 12, "#fff"))
        b.append(_t(x0, y + 44, note, 12, MUTED))
    b.append(_arrow(690, 150, 760, 150))
    b.append(f'<circle cx="900" cy="150" r="105" fill="#fff" stroke="{BAD}" stroke-width="2"/>')
    b.append(_t(900, 145, pct(baseline), 58, BAD, "middle", 600, True))
    b.append(_t(900, 178, "Falcon 3B · Arabic", 12, MUTED, "middle"))
    b.append(_t(900, 196, "first try · 244 problems", 11.5, MUTED, "middle"))
    b.append(
        _t(
            900,
            290,
            "language of the training data ≠ language of the users",
            15,
            NAVY,
            "middle",
            600,
            True,
        )
    )
    return _svg(1080, 310, "".join(b))


def idea_svg() -> str:
    b = []
    b.append(_box(20, 60, 300, 110, "", ""))
    b.append(
        f'<text x="170" y="108" font-size="22" fill="{NAVY}" text-anchor="middle" font-family="Noto Naskh Arabic, Amiri, serif">{html.escape("خُفِّض ٨٠٠ بنسبة ١٠٪ ثم ٢٠٪ → ٦٨٠")}</text>'
    )
    b.append(_t(170, 140, "Falcon says (Arabic)", 12, MUTED, "middle"))
    b.append(_arrow(322, 115, 388, 115))
    b.append(_t(355, 50, "translate", 11, MUTED, "middle"))
    b.append(_box(390, 60, 330, 110, "", ""))
    b.append(
        f'<text x="555" y="110" font-size="15" fill="{NAVY}" text-anchor="middle" font-family="ui-monospace, Menlo, monospace">(800:ℝ)·(1-0.10)·(1-0.20) = 680</text>'
    )
    b.append(_t(555, 140, "Lean 4 proposition P", 12, MUTED, "middle"))
    b.append(_arrow(722, 115, 788, 115))
    b.append(_t(755, 50, "kernel", 11, MUTED, "middle"))
    b.append(_box(790, 60, 270, 110, "Lean 4 kernel", "tries P and ¬P", fill="#f6f8fc", sw=1.8))
    # three outcomes
    outs = [
        ("verified", OK, "⊢ P"),
        ("refuted", BAD, "⊢ ¬P"),
        ("unknown", "#a8690b", "no proof either way"),
    ]
    for i, (lab, col, sub) in enumerate(outs):
        x = 780 + i * 100
        b.append(
            _arrow(
                925,
                172,
                x + 40,
                215,
                col if col != OK else NAVY,
                marker="ah" if col != BAD else "ahr",
            )
        )
        b.append(
            f'<rect x="{x - 4}" y="218" width="88" height="24" rx="12" fill="#fff" stroke="{col}"/>'
        )
        b.append(_t(x + 40, 235, lab, 11.5, col, "middle"))
        b.append(_t(x + 40, 262, sub, 11, MUTED, "middle"))
    b.append(
        _t(
            540,
            235,
            "truth of a math claim does not depend on its language",
            17,
            NAVY,
            "middle",
            600,
            True,
        )
    )
    b.append(
        _t(540, 262, "so we do not ask a second LLM — we ask a proof kernel", 13, MUTED, "middle")
    )
    return _svg(1080, 285, "".join(b))


def pregroup_svg() -> str:
    """Type cancellation for  كتب أحمد الدرس  (VSO) drawn with under-links, plus the 5-friends graph."""
    b = []
    words = [("كتب", "s · oˡ · πˡ", "wrote"), ("أحمد", "π", "Ahmad"), ("الدرس", "o", "the lesson")]
    xs = [120, 300, 460]
    for (w, ty, gl), x in zip(words, xs, strict=True):
        b.append(
            f'<text x="{x}" y="50" font-size="30" fill="{NAVY}" text-anchor="middle" font-family="Noto Naskh Arabic, Amiri, serif">{w}</text>'
        )
        b.append(_t(x, 72, gl, 11, MUTED, "middle"))
        b.append(
            _t(x, 105, ty, 17, NAVY, "middle", extra='font-family="ui-monospace, Menlo, monospace"')
        )
    # links: πˡ (right part of first) with π ; oˡ with o
    b.append(f'<path d="M165 112 Q 232 160 300 112" fill="none" stroke="{OK}" stroke-width="1.8"/>')
    b.append(f'<path d="M140 112 Q 300 200 460 112" fill="none" stroke="{OK}" stroke-width="1.8"/>')
    b.append(_t(232, 150, "πˡ·π → 1", 11, OK, "middle"))
    b.append(_t(300, 195, "oˡ·o → 1", 11, OK, "middle"))
    b.append(_arrow(300, 215, 300, 245))
    b.append(_t(300, 268, "s", 26, NAVY, "middle", 600, True))
    b.append(
        _t(
            300,
            288,
            "types cancel ⇒ sentence ⇒ the same derivation is the translation",
            12,
            MUTED,
            "middle",
        )
    )
    # SVO variant note
    b.append(
        _t(
            300,
            312,
            "أحمد كتب الدرس  (SVO) — different word order, same meaning: proved in Lean (vso_svo_same_meaning)",
            11.5,
            MUTED,
            "middle",
        )
    )
    # right: five friends graph
    cx, cy, r = 830, 150, 95
    pts = [
        (
            cx + r * math.cos(2 * math.pi * k / 5 - math.pi / 2),
            cy + r * math.sin(2 * math.pi * k / 5 - math.pi / 2),
        )
        for k in range(5)
    ]
    for i in range(5):
        for j in range(i + 1, 5):
            b.append(
                f'<line x1="{pts[i][0]}" y1="{pts[i][1]}" x2="{pts[j][0]}" y2="{pts[j][1]}" stroke="{LINE}" stroke-width="1.2"/>'
            )
    for x, y in pts:
        b.append(
            f'<circle cx="{x}" cy="{y}" r="16" fill="#fff" stroke="{NAVY}" stroke-width="1.5"/>'
        )
        b.append(_t(x, y + 5, "3", 14, NAVY, "middle", 600))
    b.append(_t(cx, 290, "each claims 3 friends  ⇒  Σ deg = 5 × 3 = 15  (odd)", 14, NAVY, "middle"))
    b.append(
        _t(
            cx,
            312,
            "handshake lemma: Σ deg = 2·|E| is even  ⇒  impossible  ⇒  someone lies  ✓",
            12.5,
            MUTED,
            "middle",
        )
    )
    b.append(
        f'<text x="{cx}" y="{cy + 5}" font-size="20" fill="{BAD}" text-anchor="middle" font-weight="600">∄</text>'
    )
    b.append(
        _t(
            cx,
            40,
            "∀ f : Fin 5 → Fin 5 → Bool, ¬ Regular f 3",
            14,
            NAVY,
            "middle",
            extra='font-family="ui-monospace, Menlo, monospace"',
        )
    )
    b.append(
        f'<rect x="{cx + 100}" y="{cy - 11}" width="92" height="22" rx="11" fill="#fff" stroke="{OK}"/>'
    )
    b.append(_t(cx + 146, cy + 4, "verified · 18 s", 11, OK, "middle"))
    b.append(f'<line x1="600" y1="20" x2="600" y2="320" stroke="{LINE}"/>')
    return _svg(1080, 330, "".join(b))


def live_svg() -> str:
    b = []
    # example 1 chain
    chain1 = [
        ("Falcon 3B", "٦٨٠", BAD),
        ("Lean", "⊢ ¬P", BAD),
        ("feedback", "بالعربية", NAVY),
        ("Falcon 3B", "٥٧٦", OK),
        ("Lean", "⊢ P", OK),
    ]
    b.append(_t(20, 30, "1 · catch → teach → correct", 20, NAVY, weight=600, serif=True))
    b.append(
        f'<text x="1060" y="30" font-size="17" fill="{NAVY}" text-anchor="end" font-family="Noto Naskh Arabic, Amiri, serif">{html.escape("هاتف بـ 800 درهم، خُفِّض 10٪ ثم 20٪")}</text>'
    )
    for i, (lab, val, col) in enumerate(chain1):
        x = 20 + i * 212
        b.append(
            f'<rect x="{x}" y="50" width="170" height="70" rx="6" fill="#fff" stroke="{col}" stroke-width="1.5"/>'
        )
        b.append(_t(x + 85, 74, lab, 12, MUTED, "middle"))
        b.append(
            f'<text x="{x + 85}" y="106" font-size="24" fill="{col}" text-anchor="middle" font-weight="600" font-family="Noto Naskh Arabic, Cormorant Garamond, serif">{val}</text>'
        )
        if i < 4:
            b.append(
                _arrow(
                    x + 172,
                    85,
                    x + 210,
                    85,
                    BAD if i < 2 else NAVY,
                    marker="ahr" if i < 2 else "ah",
                )
            )
    b.append(_t(20, 145, "round 1", 11, MUTED))
    b.append(_t(656, 145, "round 2 · assurance 1.0", 11, MUTED))
    b.append(f'<line x1="20" y1="165" x2="1060" y2="165" stroke="{LINE}"/>')
    # example 2 chain
    b.append(_t(20, 195, "2 · prove without understanding", 20, NAVY, weight=600, serif=True))
    b.append(
        f'<text x="1060" y="195" font-size="17" fill="{NAVY}" text-anchor="end" font-family="Noto Naskh Arabic, Amiri, serif">{html.escape("خمسة طلاب، كل واحد له ثلاثة أصدقاء — هل يكذب أحدهم؟")}</text>'
    )
    chain2 = [
        ("Falcon 3B", "نعم", NAVY),
        ("pregroup grammar", "¬ Regular f 3", NAVY),
        ("handshake lemma", "Σdeg even", NAVY),
        ("Lean", "⊢ P", OK),
        ("ask again", "memory · 0 s", MUTED),
    ]
    for i, (lab, val, col) in enumerate(chain2):
        x = 20 + i * 212
        b.append(
            f'<rect x="{x}" y="215" width="170" height="70" rx="6" fill="{"#f6f8fc" if i == 4 else "#fff"}" stroke="{col}" stroke-width="1.5"/>'
        )
        b.append(_t(x + 85, 239, lab, 12, MUTED, "middle"))
        fam = "Noto Naskh Arabic, serif" if i == 0 else "ui-monospace, Menlo, monospace"
        b.append(
            f'<text x="{x + 85}" y="{270 if i else 272}" font-size="{22 if i == 0 else 15}" fill="{col}" text-anchor="middle" font-weight="600" font-family="{fam}">{html.escape(val)}</text>'
        )
        if i < 4:
            b.append(_arrow(x + 172, 250, x + 210, 250, NAVY if i < 3 else MUTED))
    b.append(
        _t(
            20,
            310,
            "no LLM writes the Lean · nobody defines “friend” · the kernel verdict is reusable, Falcon's answer is not",
            12,
            MUTED,
        )
    )
    return _svg(1080, 325, "".join(b))


def evidence_svg(a86: dict, a244: dict) -> str:
    b = []
    groups = [("Arabic curated · 86", a86), ("Arabic scale · 244", a244)]
    x0, gw, bw, h0, hmax = 60, 300, 110, 250, 200
    for gi, (lab, s) in enumerate(groups):
        gx = x0 + gi * gw
        for k, (key, col, name) in enumerate(
            (("baseline_accuracy", "#c9d2e3", "baseline"), ("verified_accuracy", NAVY, "verified"))
        ):
            v = s[key]
            x = gx + k * (bw + 14)
            b.append(
                f'<rect x="{x}" y="{h0 - hmax * v}" width="{bw}" height="{hmax * v}" fill="{col}"/>'
            )
            b.append(
                _t(
                    x + bw / 2,
                    h0 - hmax * v - 8,
                    pct(v),
                    20,
                    NAVY if k else MUTED,
                    "middle",
                    600,
                    True,
                )
            )
            b.append(_t(x + bw / 2, h0 + 18, name, 11.5, MUTED, "middle"))
        b.append(_t(gx + bw + 7, h0 + 40, lab, 13, NAVY, "middle", 600))
        b.append(
            _arrow(
                gx + bw / 2 + 10,
                h0 - hmax * s["baseline_accuracy"] - 30,
                gx + bw + 14 + bw / 2 - 10,
                h0 - hmax * s["verified_accuracy"] - 30,
                OK,
            )
        )
    b.append(f'<line x1="{x0 - 10}" y1="{h0}" x2="{x0 + 2 * gw - 40}" y2="{h0}" stroke="{NAVY}"/>')
    # KPI column
    kx = 700
    kpis = [
        (pct(a244["detection_recall"]), "wrong answers caught by Lean", NAVY),
        (
            f"{a244['fixed_after_feedback']}/{a244['wrong_baseline']}",
            "fixed after one Arabic feedback",
            NAVY,
        ),
        (str(a244["regressions"]), "correct answers made wrong", OK),
        (str(a244["false_alarms_on_correct"]), f"false alarm in {a244['n']}", OK),
    ]
    for i, (n, lab, col) in enumerate(kpis):
        y = 55 + i * 62
        b.append(_t(kx, y, n, 34, col, "start", 600, True))
        b.append(_t(kx + 150, y - 4, lab, 13, MUTED))
        b.append(f'<line x1="{kx}" y1="{y + 14}" x2="1060" y2="{y + 14}" stroke="{LINE}"/>')
    b.append(
        _t(
            kx,
            292,
            "3B student · 34B Arabic formalizer · Lean 4 + Mathlib",
            11.5,
            MUTED,
        )
    )
    return _svg(1080, 300, "".join(b))


def product_svg() -> str:
    b = []
    b.append(_box(20, 40, 180, 80, "your app", "chat · tutor · agent"))
    b.append(_arrow(202, 80, 268, 80))
    b.append(
        _t(
            235,
            68,
            "POST /api/solve",
            10.5,
            MUTED,
            "middle",
            extra='font-family="ui-monospace, Menlo, monospace"',
        )
    )
    b.append(_box(270, 40, 220, 80, "FalconVerifier", "middleware", fill="#f6f8fc", sw=1.8))
    b.append(_arrow(492, 65, 558, 65))
    b.append(_arrow(558, 95, 492, 95))
    b.append(_box(560, 40, 160, 80, "Falcon", "unchanged"))
    b.append(_arrow(380, 122, 380, 165))
    b.append(_box(270, 168, 220, 70, "Lean 4", "verdicts, not vibes", fill="#fff"))
    b.append(_arrow(268, 80, 202, 80, OK))
    b.append(_t(235, 138, "answer + assurance", 10.5, OK, "middle"))
    # flywheel
    b.append(_arrow(492, 203, 558, 203, BAD, marker="ahr"))
    b.append(_box(560, 168, 160, 70, "DPO pairs", "294 · Lean-labelled", stroke=BAD))
    b.append(_arrow(640, 166, 640, 124, BAD, "4 4", "ahr"))
    b.append(_t(665, 150, "train", 11, BAD))
    # right column: deploy
    b.append(f'<line x1="770" y1="30" x2="770" y2="245" stroke="{LINE}"/>')
    items = [
        ("⬢", "Docker · Lean + Mathlib inside"),
        ("🔒", "HTTPS · rate limits · access token"),
        ("⟲", "memory · repeated claims in 0 s"),
        ("⌥", "web UI · CLI · API · open source"),
    ]
    for i, (ic, txt) in enumerate(items):
        y = 55 + i * 50
        b.append(_t(800, y, ic, 20, NAVY))
        b.append(_t(835, y - 2, txt, 14, NAVY))
    return _svg(1080, 250, "".join(b))


def build() -> str:
    a86 = summary("falcon3b_arabic")
    a244 = summary("falcon3b_arabic_scale")
    mark = (STATIC / "mark.png").resolve().as_uri()
    logo = (STATIC / "chaosbutterfly_logo.png").resolve().as_uri()
    foot = f'<div class="foot"><span><img src="{mark}" alt="">ChaosButterfly · FalconVerifier</span><span class="pg"></span></div>'
    slides = [
        f"""<section class="slide"><div class="brand"><img src="{logo}" alt="ChaosButterfly"></div>
        <h1>FalconVerifier</h1>
        <p class="lede">Falcon says it → Lean 4 proves it, or refutes it → Falcon learns. In Arabic.</p>
        <p class="note">ChaosButterfly · Hub71 Fish Tank · 5 min</p>{foot}</section>""",
        slide(
            "01 · the gap",
            "<h2>Region's model · Arabic users · English data</h2>"
            + gap_svg(a244["baseline_accuracy"]),
        ),
        slide("02 · the idea", "<h2>Don't ask another LLM. Ask a proof kernel.</h2>" + idea_svg()),
        slide("03 · pipeline", "<h2>One loop, six stages</h2>" + pipeline_svg()),
        slide(
            "04 · Arabic → Lean, deterministically",
            "<h2>Pregroup grammar: types cancel ⇒ translation is a proof</h2>" + pregroup_svg(),
        ),
        slide("05 · live", "<h2>Two examples, one screen</h2>" + live_svg()),
        slide(
            "06 · evidence",
            "<h2>Falcon verifies Falcon — 0 regressions</h2>"
            + evidence_svg(a86, a244)
            + '<p class="note">every bar links to its problems, traces and Lean sources on /benchmark</p>',
        ),
        slide(
            "07 · product",
            "<h2>Middleware, not a model</h2>"
            + product_svg()
            + '<p class="note">limits, said out loud: Lean checks what was formalized · out-of-fragment steps depend on the 34B formalizer · proof-style problems → unknown</p>',
        ),
        f"""<section class="slide"><div class="brand"><img src="{logo}" alt="ChaosButterfly"></div>
        <h1>Trust in Arabic, proved in Lean.</h1>
        <p class="lede">Falcon → Lean 4 → Falcon</p>
        <p style="color:var(--muted)">github.com/hw4375-collab/FalconVerifer · live demo →</p>{foot}</section>""",
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
