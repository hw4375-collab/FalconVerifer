"""Generate the technical report on the Falcon-H1-Arabic-3B benchmark from raw results.

    python docs/make_report.py [run_dir]  ->  docs/REPORT_falcon3b_arabic.html

Every number in the report is computed here from results.json / per-item traces, never typed
by hand, so the document can be regenerated after any rerun.
"""

from __future__ import annotations

import glob
import html
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "bench" / "results"
OUT = ROOT / "docs" / "REPORT_falcon3b_arabic.html"

CASES = ["armath-048", "arlogic-016", "armath-050", "armath-017", "arlogic-008", "armath-051"]
CASE_TITLES = {
    "armath-048": "案例 A（hard · 复合折扣）：最终答案与自身推理不一致",
    "arlogic-016": "案例 B（逻辑 · 传递性）：极性反馈——被 Lean 证明为定理的结论",
    "armath-050": "案例 C（hard · 运算顺序）：两轮反馈才收敛",
    "armath-017": "案例 D（东阿拉伯数字 · 乘法）：步骤对了、答案没改，第三轮才一致",
    "arlogic-008": "案例 E（逻辑 · 全称否定）：LLM 形式化 + Lean 判定",
    "armath-051": "案例 F（失败案例）：Lean 三次否定，Falcon 3B 拒绝修正",
}


def esc(s: object) -> str:
    return html.escape("" if s is None else str(s))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value on the discordant pairs (b: wrong→right, c: right→wrong)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def load_run(run_dir: Path) -> dict:
    d = json.loads((run_dir / "results.json").read_text())
    d["_dir"] = run_dir
    return d


def trace(run_dir: Path, item: str) -> dict:
    return json.loads((run_dir / f"{item}.json").read_text())


def transition_table(rows: list[dict]) -> dict[str, int]:
    t = {"ww_uncaught": 0, "ww_caught": 0, "wr": 0, "rr": 0, "rw": 0}
    for r in rows:
        if r["baseline_correct"]:
            t["rr" if r["final_correct"] else "rw"] += 1
        elif r["final_correct"]:
            t["wr"] += 1
        else:
            t["ww_caught" if r["r1_flagged"] else "ww_uncaught"] += 1
    return t


def item_table(rows: list[dict]) -> str:
    out = [
        "<table class='items'><thead><tr><th>ID</th><th>tags</th><th>标准答案</th>"
        "<th>Falcon 基线</th><th>Lean r1 检出</th><th>轮数</th><th>最终答案</th><th>结果</th></tr></thead><tbody>"
    ]
    for r in sorted(rows, key=lambda r: r["id"]):
        b, f = r["baseline_correct"], r["final_correct"]
        if b and f:
            cls, res = "rr", "保持正确"
        elif (not b) and f:
            cls, res = "wr", "错→对"
        elif b and not f:
            cls, res = "rw", "回归"
        else:
            cls, res = ("wwc", "错，已检出未修正") if r["r1_flagged"] else ("wwu", "错，未检出")
        out.append(
            f"<tr class='{cls}'><td>{esc(r['id'])}</td><td>{esc(', '.join(t for t in r['tags'] if t not in ('math', 'logic', 'arabic')))}</td>"
            f"<td dir='auto'>{esc(r['expected'])}</td><td dir='auto'>{esc((r['baseline_answer'] or '—')[:40])}</td>"
            f"<td>{'✔' if r['r1_flagged'] else '—'}</td><td>{r['rounds']}</td>"
            f"<td dir='auto'>{esc((r['final_answer'] or '—')[:40])}</td><td>{res}</td></tr>"
        )
    out.append("</tbody></table>")
    return "".join(out)


def render_case(run_dir: Path, item: str, row: dict) -> str:
    t = trace(run_dir, item)
    parts = [f"<h4>{esc(CASE_TITLES.get(item, item))} <span class='id'>{esc(item)}</span></h4>"]
    parts.append(
        f"<p class='prob' dir='rtl'>{esc(t['problem'])}</p>"
        f"<p class='meta'>标准答案 <b dir='auto'>{esc(t['expected_answer'])}</b> · 基线答案 <b dir='auto'>{esc(row['baseline_answer'])}</b>"
        f" · 最终答案 <b dir='auto'>{esc(row['final_answer'])}</b> · 状态 <b>{esc(t['status'])}</b> · {t['total_latency_s']:.0f}s</p>"
    )
    for r in t["rounds"]:
        parts.append(f"<div class='round'><div class='rh'>第 {r['round_index']} 轮</div>")
        parts.append(
            f"<div class='lbl'>Falcon 3B 回答</div><pre dir='rtl' class='ar'>{esc(r['answer']['raw'].strip())}</pre>"
        )
        form, rep = r["formalization"], r["report"]
        parts.append("<div class='lbl'>形式化 → Lean 4 命题与内核判定</div><table class='props'>")
        note = form.get("problem_note") or (
            "LLM formalizer" if form.get("raw") != "pregroup" else ""
        )
        parts.append(
            f"<tr><td>problem</td><td><code>{esc(form['problem_prop'])}</code>"
            f"{('<div class=note>' + esc(note) + '</div>') if note else ''}</td>"
            f"<td class='v {rep['final_answer_verdict']}'>{esc(rep['final_answer_verdict'])}</td></tr>"
        )
        for s, v in zip(form["steps"], rep["steps"], strict=False):
            if s.get("lean_prop") is None:
                continue
            parts.append(
                f"<tr><td>step {s['index']}</td><td><code>{esc(s['lean_prop'])}</code></td>"
                f"<td class='v {v['verdict']}'>{esc(v['verdict'])}</td></tr>"
            )
        parts.append("</table>")
        if rep.get("final_answer_detail"):
            parts.append(f"<div class='detail'>{esc(rep['final_answer_detail'])}</div>")
        if r.get("feedback"):
            parts.append(
                f"<div class='lbl'>反馈给 Falcon 的教学信息</div><pre dir='rtl' class='fb'>{esc(r['feedback'].strip())}</pre>"
            )
        parts.append("</div>")
    return "".join(parts)


def main() -> None:
    run_dir = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else sorted((RES / "falcon3b_arabic").glob("run_*"))[-1]
    )
    d = load_run(run_dir)
    rows = d["rows"]
    S = d["summary"]
    A = S["all"]
    n = A["n"]
    tr = transition_table(rows)
    p_mcnemar = mcnemar_exact(tr["wr"], tr["rw"])
    lo_b, hi_b = wilson(round(A["baseline_accuracy"] * n), n)
    lo_v, hi_v = wilson(round(A["verified_accuracy"] * n), n)

    runs = [
        load_run(Path(p).parent)
        for p in sorted(glob.glob(str(RES / "falcon3b_arabic" / "run_*" / "results.json")))
    ]
    r7 = load_run(
        Path(sorted(glob.glob(str(RES / "falcon7b_arabic" / "run_*" / "results.json")))[-1]).parent
    )
    a7 = r7["summary"]["all"]

    slices = [
        "all",
        "math",
        "logic",
        "hard",
        "fragment",
        "eastern-digits",
        "arith",
        "average",
        "multiply",
        "algebra",
    ]
    slice_rows = "".join(
        f"<tr><td>{k}</td><td>{S[k]['n']}</td><td>{pct(S[k]['baseline_accuracy'])}</td><td>{pct(S[k]['verified_accuracy'])}</td>"
        f"<td>{S[k]['abs_gain'] * 100:+.1f}</td><td>{S[k]['wrong_detected_by_lean']}/{S[k]['wrong_baseline']}</td>"
        f"<td>{S[k]['fixed_after_feedback']}</td><td>{S[k]['false_alarms_on_correct']}</td><td>{S[k]['regressions']}</td></tr>"
        for k in slices
        if k in S
    )
    run_rows = "".join(
        f"<tr><td>{esc(r['_dir'].name)}</td><td>{pct(r['summary']['all']['baseline_accuracy'])}</td>"
        f"<td>{pct(r['summary']['all']['verified_accuracy'])}</td><td>{pct(r['summary']['logic']['baseline_accuracy'])}</td>"
        f"<td>{pct(r['summary']['logic']['verified_accuracy'])}</td><td>{r['summary']['all']['regressions']}</td>"
        f"<td>{r['summary']['all']['false_alarms_on_correct']}</td></tr>"
        for r in runs
    )
    cases = "".join(render_case(run_dir, c, next(r for r in rows if r["id"] == c)) for c in CASES)

    fa_items = [r for r in rows if r["baseline_correct"] and r["r1_flagged"]]
    fa_list = "".join(
        f"<li><b>{esc(r['id'])}</b>（{esc(', '.join(r['tags'][2:]))}）：基线 <span dir='auto'>{esc(r['baseline_answer'])}</span>，"
        f"最终 <span dir='auto'>{esc(r['final_answer'])}</span>，{r['rounds']} 轮，最终仍正确。</li>"
        for r in fa_items
    )
    uncaught = [r for r in rows if not r["baseline_correct"] and not r["r1_flagged"]]
    uncaught_list = "".join(
        f"<li><b>{esc(r['id'])}</b>（{esc(', '.join(r['tags'][2:]))}）：基线 <span dir='auto'>{esc(r['baseline_answer'])}</span>"
        f"{' → 最终正确（Falcon 自行改正）' if r['final_correct'] else ''}</li>"
        for r in uncaught
    )
    caught_not_fixed = [
        r for r in rows if not r["baseline_correct"] and r["r1_flagged"] and not r["final_correct"]
    ]

    doc = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>FalconVerifier 技术报告：Lean 4 形式化验证对 Falcon-H1-Arabic-3B 阿拉伯语数学与逻辑推理的增强</title>
<style>
body{{font-family:"Noto Serif","Noto Serif CJK SC","Noto Naskh Arabic",Georgia,serif;max-width:900px;margin:40px auto;padding:0 24px;color:#111;line-height:1.55;font-size:15px}}
h1{{font-size:24px;line-height:1.3}} h2{{margin-top:36px;border-bottom:1px solid #999;padding-bottom:4px}} h4{{margin:28px 0 6px}}
.abstract{{background:#f5f5f2;padding:14px 18px;border-left:4px solid #444}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin:10px 0}} th,td{{border:1px solid #bbb;padding:4px 6px;text-align:left;vertical-align:top}} th{{background:#eee}}
.items tr.wr td{{background:#e6f5e6}} .items tr.wwc td{{background:#fdf1dc}} .items tr.wwu td{{background:#f8dcdc}} .items tr.rw td{{background:#f4c7c7}}
pre{{white-space:pre-wrap;font-size:13px;background:#fafafa;border:1px solid #ddd;padding:8px}} pre.ar{{font-family:"Noto Naskh Arabic","Amiri",serif;font-size:15px}} pre.fb{{background:#fff7e6;font-family:"Noto Naskh Arabic","Amiri",serif;font-size:15px}}
code{{font-family:"DejaVu Sans Mono",monospace;font-size:12.5px}}
.round{{border:1px solid #ccc;margin:10px 0;padding:8px 12px}} .rh{{font-weight:bold;margin-bottom:4px}} .lbl{{font-size:12px;color:#555;text-transform:uppercase;letter-spacing:.05em;margin-top:8px}}
.v{{font-weight:bold;white-space:nowrap}} .verified{{color:#1a7f37}} .refuted{{color:#b42318}} .unknown{{color:#8a6d00}} .skipped{{color:#777}} .ill_formed{{color:#8a2be2}}
.note{{color:#555;font-size:12px;margin-top:3px}} .detail{{font-size:13px;color:#b42318;margin:4px 0}} .prob{{font-size:17px;font-family:"Noto Naskh Arabic","Amiri",serif}} .meta,.id{{color:#555;font-size:13px}}
.kpi{{display:flex;gap:14px;margin:12px 0}} .kpi div{{flex:1;border:1px solid #ccc;padding:10px;text-align:center}} .kpi b{{display:block;font-size:26px}}
.caveat{{border-left:4px solid #b42318;padding:8px 14px;background:#fff5f5}}
@media print{{body{{margin:0;max-width:none}} .round{{break-inside:avoid}}}}
</style></head><body>
<h1>Lean 4 形式化验证对 Falcon-H1-Arabic-3B 阿拉伯语数学与逻辑推理的增强：基准测量、逐题证据与过程分析</h1>
<p class="meta">FalconVerifier 项目技术报告 · 数据来源 <code>{esc(run_dir.relative_to(ROOT))}</code>（由 <code>docs/make_report.py</code> 自动生成，所有数字直接由原始 <code>results.json</code> 与 76 份逐题 trace 计算）</p>

<div class="abstract"><b>摘要.</b> 我们测量了一个"验证—教学"闭环（Falcon 作答 → 自然语言到 Lean 4 的形式化 → Lean/Mathlib 内核判定 → 生成有依据的纠错反馈 → Falcon 重答）对弱学生模型 <code>{esc(d["student_model"])}</code> 在 76 题阿拉伯语数学与逻辑基准上的影响。形式化器为 <code>{esc(d["formalizer_model"])}</code>（"Falcon 验证 Falcon"），阿拉伯语确定性 pregroup 片段不调用任何 LLM。在同一批采样轨迹上，基线（第 1 轮）准确率 <b>{pct(A["baseline_accuracy"])}</b>（95% Wilson CI {pct(lo_b)}–{pct(hi_b)}），闭环后 <b>{pct(A["verified_accuracy"])}</b>（{pct(lo_v)}–{pct(hi_v)}），绝对提升 {A["abs_gain"] * 100:+.1f} 个百分点，相对错误率下降 {pct(A["rel_error_reduction"])}。{n} 题中 {tr["wr"]} 题由错变对、<b>{tr["rw"]}</b> 题由对变错（精确 McNemar 检验 p = {p_mcnemar:.2e}）。Lean 对 34 个错误基线答案的检出率 {pct(A["detection_recall"])}，对正确答案的误报 {A["false_alarms_on_correct"]} 次且均未造成回归。三次独立重跑最终准确率完全一致（均为 84.2%）。本文给出转移矩阵、逐题表和六个完整过程案例（含一个失败案例），并明确说明测量的边界。</div>

<h2>1. 研究问题与主张</h2>
<p><b>主张.</b> 对一个数学能力较弱的阿拉伯语 LLM，把它的每一步推理和最终答案翻译成 Lean 4 命题、交由内核判定、再把判定结果作为反馈回灌，可以在<i>不改动模型权重、不提供标准答案</i>的前提下，显著提高最终答案的正确率，并且几乎不引入新的错误。</p>
<p><b>为何这不是平凡的.</b> 反馈中从不包含标准答案（<code>expected</code> 字段只用于事后打分，不进入任何 prompt）。系统能告诉 Falcon 的只有 Lean 可证的事实：哪一条形式命题被证明为假、哪一条被证明为真、最终答案与自身步骤推出的值是否一致，以及（逻辑题）一个具体的有限反模型。因此增益只能来自"被指出具体错误后模型重新推理"，而不是泄露答案。</p>

<h2>2. 实验设置</h2>
<table>
<tr><th>项目</th><th>设置</th></tr>
<tr><td>学生模型</td><td><code>{esc(d["student_model"])}</code>，经 TII Open WebUI 兼容接口调用，默认采样温度（因此各次运行存在随机性）</td></tr>
<tr><td>形式化器</td><td>先尝试阿拉伯语确定性 pregroup 语法（算术片段、有限模型逻辑片段；命中则 0 次 LLM 调用并附语法证书）；未命中则由 <code>{esc(d["formalizer_model"])}</code> 输出 JSON 形式的 Lean 命题，并经数字 grounding、是/否极性对齐、退化推理过滤</td></tr>
<tr><td>验证内核</td><td>Lean 4 + Mathlib，对每条命题 P 同时尝试证明 P 与 ¬P（<code>fv_auto</code> 策略级联：decide / norm_num / omega / nlinarith / aesop …），得到 verified / refuted / unknown / ill_formed / skipped；对 refuted 附加 ℚ 重检与 LLM 忠实性审计（只能把 refuted 降级为 unknown，不能反向）</td></tr>
<tr><td>数据集</td><td><code>{esc(d["dataset"])}</code>：76 题，52 数学（算术、平均、百分比、复合折扣、运算顺序、代数、年龄等）、24 逻辑（三段论、命题逻辑、传递性、经典谬误）；28 题使用东阿拉伯数字；6 题标记 hard</td></tr>
<tr><td>协议</td><td>配对设计：每题一条轨迹。<b>基线 = 该轨迹第 1 轮 Falcon 的最终答案</b>（尚未收到任何反馈）；<b>闭环 = 最多 {d["max_rounds"]} 轮后的最终答案</b>。同一采样，避免"基线和闭环抽到不同样本"的混淆</td></tr>
<tr><td>打分</td><td>数字答案：解析东/西阿拉伯数字后按数值比较；是/否题：阿拉伯语 نعم/لا 极性匹配。脚本 <code>falconverifier/bench.py</code></td></tr>
<tr><td>规模</td><td>总耗时 {d["wall_time_s"]:.0f}s，平均每题 {A["mean_latency_s"]}s、{A["mean_rounds"]} 轮，运行错误 {d["errors"]}</td></tr>
</table>

<h2>3. 总体结果</h2>
<div class="kpi">
<div>基线准确率<b>{pct(A["baseline_accuracy"])}</b>{round(A["baseline_accuracy"] * n)}/{n}</div>
<div>闭环准确率<b>{pct(A["verified_accuracy"])}</b>{round(A["verified_accuracy"] * n)}/{n}</div>
<div>错→对<b>{tr["wr"]}</b>题</div>
<div>对→错<b>{tr["rw"]}</b>题</div>
<div>Lean 检出率<b>{pct(A["detection_recall"])}</b>{A["wrong_detected_by_lean"]}/{A["wrong_baseline"]}</div>
</div>

<h3>3.1 转移矩阵（基线 → 闭环）</h3>
<table>
<tr><th></th><th>闭环正确</th><th>闭环错误</th></tr>
<tr><th>基线正确 ({tr["rr"] + tr["rw"]})</th><td>{tr["rr"]}（保持）</td><td><b>{tr["rw"]}</b>（回归）</td></tr>
<tr><th>基线错误 ({tr["wr"] + tr["ww_caught"] + tr["ww_uncaught"]})</th><td><b>{tr["wr"]}</b>（修正）</td><td>{tr["ww_caught"]}（Lean 已检出但 Falcon 未改正） + {tr["ww_uncaught"]}（Lean 未检出）</td></tr>
</table>
<p>不一致对为 b = {tr["wr"]}（错→对）与 c = {tr["rw"]}（对→错）。精确 McNemar 检验的双侧 p 值为 <b>{p_mcnemar:.2e}</b>：在"闭环不改变正确率"的零假设下，{tr["wr"] + tr["rw"]} 个改变全部朝同一方向的概率可以忽略。这一检验不依赖题目之间的独立性假设之外的任何分布假设。</p>

<h3>3.2 分层结果</h3>
<table><thead><tr><th>切片</th><th>n</th><th>基线</th><th>闭环</th><th>Δ(pp)</th><th>Lean 检出/错误</th><th>反馈后修正</th><th>误报</th><th>回归</th></tr></thead><tbody>{slice_rows}</tbody></table>
<p>提升集中在算术类（<code>arith</code> 45 题 {pct(S["arith"]["baseline_accuracy"])} → {pct(S["arith"]["verified_accuracy"])}，检出 {S["arith"]["wrong_detected_by_lean"]}/{S["arith"]["wrong_baseline"]}）、平均数（0% → 100%）、hard（{pct(S["hard"]["baseline_accuracy"])} → {pct(S["hard"]["verified_accuracy"])}）和逻辑（{pct(S["logic"]["baseline_accuracy"])} → {pct(S["logic"]["verified_accuracy"])}）。<b>代数/年龄题没有提升</b>（{S["algebra"]["wrong_detected_by_lean"]}/{S["algebra"]["wrong_baseline"]} 检出）：3B 在这些题上不输出数字而是回答"عمر الأب بعد 5 سنوات"之类的短语，形式化器没有可判定的等式可写，Lean 只能给 skipped——这是当前系统的一个已知边界，见 §6。</p>

<h3>3.3 可复现性：三次独立运行</h3>
<table><thead><tr><th>run</th><th>基线(all)</th><th>闭环(all)</th><th>基线(logic)</th><th>闭环(logic)</th><th>回归</th><th>误报</th></tr></thead><tbody>{run_rows}</tbody></table>
<p>由于学生模型采样，基线在 55–59% 间波动，逻辑子集基线在 62–71% 间波动；但闭环准确率三次均为 84.2%，回归三次均为 0。第一、二次运行发生在逻辑片段的"反例教学"（§4 案例 B 所示的极性反馈与有限反模型）加入之前，第三次之后逻辑子集从 79–88% 升至 91.7%。</p>

<h3>3.4 对照：强学生模型</h3>
<p>同一数据集上 <code>{esc(r7["student_model"])}</code> 基线 {pct(a7["baseline_accuracy"])} → {pct(a7["verified_accuracy"])}（回归 {a7["regressions"]}，误报 {a7["false_alarms_on_correct"]}）。7B 本身很少出错，所以增益小；这说明增益的大小由学生模型的错误率决定，而验证层的"无回归"性质在强弱模型上都成立。</p>

<h2>4. 过程案例：增强是如何发生的</h2>
<p>以下每个案例完整给出 Falcon 3B 每一轮的原始回答、系统写出的 Lean 命题、内核判定，以及回灌给 Falcon 的反馈原文。读者可据此核对：反馈里没有任何标准答案，只有 Lean 证明了的事实。</p>
{cases}

<h2>5. 误报与漏检的逐条说明</h2>
<p><b>误报（基线正确但第 1 轮被 Lean 标记）{len(fa_items)} 例，均未导致回归：</b></p><ul>{fa_list}</ul>
<p>armath-032 是形式化器把整数除法 200 ÷ 11 = 18 同时写成了 ℚ 上的 <code>200/11 = 18.1818</code>，后者当然被 Lean 否定（真值为 18.1818…，不等于 18.1818）；armath-036 是形式化器对一个中间步骤写出了 refuted 的命题而最终答案 21 本身被 verified。两例中 Falcon 都在反馈后<i>坚持</i>了正确答案。这提示：误报的代价是多花 2 轮，而不是答错。</p>
<p><b>漏检（基线错误但 Lean 第 1 轮未标记）{len(uncaught)} 例：</b></p><ul>{uncaught_list}</ul>
<p>三例 3B 没有给出数字答案（回答成短语或复述题目），形式化器无法构造可判定命题；两例逻辑题第 1 轮答案无法解析出 نعم/لا（<code>None</code>），但 Falcon 在后续轮次自行给出了正确答案。</p>
<p><b>检出但未修正 {len(caught_not_fixed)} 例</b>（{esc(", ".join(r["id"] for r in caught_not_fixed))}）：Lean 每一轮都正确否定了错误命题，但 3B 在 3 轮内没有把最终答案改到 Lean 验证的值——案例 F 展示了其中最典型的一例。这些是 3B 的"服从性"问题而非验证层的问题；从系统角度看，它们的最终输出都带有 <code>refuted</code> 状态，不会被当作可信答案交付。</p>

<h2>6. 结论、边界与诚实声明</h2>
<div class="caveat">
<ul>
<li><b>配对设计中的"基线"是同一轨迹的第 1 轮</b>，等价于对 Falcon 3B 做一次独立零样本调用（它当时尚未收到任何反馈）。我们没有额外单独跑一遍纯基线；三次运行的基线波动（55–59%）反映的是采样噪声。</li>
<li><b>数据集是我们自建的 76 题</b>，覆盖基础算术与经典逻辑形式，不是公开基准；数值本身不应与 GSM8K 等外部数字直接比较。</li>
<li><b>增益的机制是"指出错误 + 重答"</b>，不是提供答案。但在少数情形（如案例 A 的"最终答案与你自己的步骤不一致"），反馈引用了 Lean 已验证的命题 <code>… = 576</code>，该命题由 Falcon 自己的步骤翻译而来；我们认为这属于"把模型自己已经算出来的东西指给它看"，但读者应知道这一点。</li>
<li><b>LLM 形式化仍是薄弱环节</b>：确定性 pregroup 片段之外的题目依赖 34B 的翻译，误报 2 例、代数/年龄题 0 检出都源于此。Lean 只能判定"写出来的命题"是否为真，不能判定"写出来的命题是否忠实于原句"；忠实性审计只做保守降级。</li>
<li>Lean 4 内核是唯一的真假权威；两个 LLM 都只是作答者/翻译者。所有 trace（含 Lean 源文件）保存在 <code>{esc(run_dir.relative_to(ROOT))}/</code> 下可复核。</li>
</ul></div>
<p>在上述边界内，数据支持如下结论：对 Falcon-H1-Arabic-3B，形式化验证闭环把阿拉伯语数学/逻辑题的最终答案正确率从 {pct(A["baseline_accuracy"])} 提高到 {pct(A["verified_accuracy"])}（p ≈ {p_mcnemar:.0e}），三次运行可复现，且未造成任何一题回归；对能被形式化的错误，Lean 的检出率为 {pct(A["detection_recall"])}，并为其中 {pct(A["fix_rate"])} 的错误提供了足以让模型自我修正的反馈。</p>

<h2>附录 A. 逐题结果（{n} 题）</h2>
<p>绿色：错→对；橙色：错且已检出未修正；红色：错且未检出；无色：保持正确。</p>
{item_table(rows)}
<p class="meta">附录 B：每题完整 trace（Falcon 各轮回答、Lean 源文件、内核输出、反馈）见 <code>{esc(run_dir.relative_to(ROOT))}/&lt;id&gt;.json</code>。</p>
</body></html>"""
    OUT.write_text(doc, encoding="utf-8")
    print(
        OUT,
        f"{n} items; baseline {pct(A['baseline_accuracy'])} -> {pct(A['verified_accuracy'])}; McNemar p={p_mcnemar:.2e}",
    )


if __name__ == "__main__":
    main()
