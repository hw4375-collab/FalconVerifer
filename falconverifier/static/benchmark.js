const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (x) => (x == null ? "–" : (x * 100).toFixed(0) + "%");
const pct1 = (x) => (x == null ? "–" : (x * 100).toFixed(1) + "%");

// Display order + human labels; anything else in results/ is appended alphabetically.
const RUN_LABELS = {
  falcon3b_arabic: "Arabic benchmark · Falcon-H1 3B Arabic (86 problems)",
  falcon3b_arabic_scale: "Arabic scale set · Falcon-H1 3B Arabic (245 generated problems)",
  falcon7b_arabic: "Arabic benchmark · Falcon-H1 7B (control: strong student)",
  falcon3b_formalizer: "English benchmark · Falcon-H1 3B Arabic",
  falcon3b_formalizer_hard: "English hard tier · Falcon-H1 3B Arabic",
  falcon3b_v2: "English math · Falcon-H1 3B Arabic",
  falcon_formalizer: "English benchmark · Falcon-H1 7B",
  falcon_formalizer_hard: "English hard tier · Falcon-H1 7B",
};
const CHART_RUNS = ["falcon3b_arabic", "falcon3b_arabic_scale", "falcon7b_arabic"];
const CHART_LABELS = { falcon3b_arabic: "3B · 86 Arabic", falcon3b_arabic_scale: "3B · 245 Arabic", falcon7b_arabic: "7B · 86 Arabic" };

// Which source file makes a slice decidable — so each row can link to the code that judged it.
const CODE_FOR_TAG = {
  arith: "falconverifier/arabic.py", percent: "falconverifier/arabic.py", "compound-percent": "falconverifier/arabic.py",
  "order-of-operations": "falconverifier/arabic.py", "eastern-digits": "falconverifier/arabic.py", multiply: "falconverifier/arabic.py",
  money: "falconverifier/formalizer.py", average: "falconverifier/formalizer.py", division: "falconverifier/formalizer.py",
  algebra: "falconverifier/formalizer.py", age: "falconverifier/formalizer.py", linear: "falconverifier/formalizer.py",
  logic: "falconverifier/arabic_logic.py", syllogism: "falconverifier/arabic_logic.py", valid: "falconverifier/arabic_logic.py",
  invalid: "falconverifier/arabic_logic.py", transitivity: "falconverifier/arabic_logic.py", ordering: "falconverifier/arabic_logic.py",
  "illicit-conversion": "falconverifier/arabic_logic.py", "undistributed-middle": "falconverifier/arabic_logic.py",
  "affirming-consequent": "falconverifier/arabic_logic.py", "denying-antecedent": "falconverifier/arabic_logic.py",
  propositional: "falconverifier/arabic_logic.py", "modus-ponens": "falconverifier/arabic_logic.py", "modus-tollens": "falconverifier/arabic_logic.py",
  relation: "falconverifier/arabic_graph.py", handshake: "falconverifier/arabic_graph.py", parity: "falconverifier/arabic_graph.py",
  "degree-bound": "falconverifier/arabic_graph.py", witness: "falconverifier/arabic_graph.py",
  fragment: "docs/ARABIC.md", math: "falconverifier/formalizer.py", hard: "bench/make_dataset_ar.py",
};
const LEAN_FOR_TAG = {
  relation: "lean/FalconVerifier/Graph.lean", handshake: "lean/FalconVerifier/Graph.lean", parity: "lean/FalconVerifier/Graph.lean",
  "degree-bound": "lean/FalconVerifier/Graph.lean", witness: "lean/FalconVerifier/Graph.lean",
  fragment: "lean/FalconVerifier/Arabic", logic: "lean/FalconVerifier/Arabic",
};

let GH = "";
const gh = (path) => `${GH}/${path}`;

function drawChart(runs) {
  const svg = $("#chart");
  const groups = [];
  for (const k of CHART_RUNS) {
    const r = runs[k];
    if (!r) continue;
    for (const sl of ["all", "math", "logic"]) {
      const s = r.summary[sl];
      if (s) groups.push({ label: `${CHART_LABELS[k]} · ${sl}`, n: s.n, base: s.baseline_accuracy, ver: s.verified_accuracy, gain: s.abs_gain });
    }
  }
  if (!groups.length) { svg.outerHTML = '<p class="muted">no benchmark results yet</p>'; return; }
  const W = 1100, H = 360, left = 50, right = 20, top = 20, bottom = 70;
  const cw = (W - left - right) / groups.length, bw = Math.min(34, cw * 0.32), ph = H - top - bottom;
  const y = (v) => top + ph * (1 - v);
  let out = "";
  for (const t of [0, 0.25, 0.5, 0.75, 1]) {
    out += `<line x1="${left}" x2="${W - right}" y1="${y(t)}" y2="${y(t)}" stroke="#d9e0ee" stroke-width="1"/>`;
    out += `<text x="${left - 8}" y="${y(t) + 4}" text-anchor="end" font-size="11" fill="#5b6b8c">${t * 100}%</text>`;
  }
  groups.forEach((g, i) => {
    const cx = left + cw * i + cw / 2;
    out += `<rect x="${cx - bw - 3}" y="${y(g.base)}" width="${bw}" height="${ph - (y(g.base) - top)}" fill="#8a94ad"/>`;
    out += `<rect x="${cx + 3}" y="${y(g.ver)}" width="${bw}" height="${ph - (y(g.ver) - top)}" fill="#0f2247"/>`;
    out += `<text x="${cx - bw / 2 - 3}" y="${y(g.base) - 5}" text-anchor="middle" font-size="11" fill="#5b6b8c">${pct(g.base)}</text>`;
    out += `<text x="${cx + bw / 2 + 3}" y="${y(g.ver) - 5}" text-anchor="middle" font-size="11" font-weight="600" fill="#0f2247">${pct(g.ver)}</text>`;
    const [a, b] = g.label.split(" · all").length > 1 ? [g.label.replace(" · all", ""), "all"] : g.label.split(/ · (?=math|logic)/);
    out += `<text x="${cx}" y="${H - bottom + 18}" text-anchor="middle" font-size="11.5" fill="#0f2247">${esc(a)}</text>`;
    out += `<text x="${cx}" y="${H - bottom + 34}" text-anchor="middle" font-size="11" fill="#5b6b8c">${esc(b)} · n=${g.n}</text>`;
    out += `<text class="ser" x="${cx}" y="${H - bottom + 56}" text-anchor="middle" font-size="17" font-weight="600" fill="${g.gain > 0 ? "#1f8a4c" : "#5b6b8c"}">${g.gain > 0 ? "+" : ""}${(g.gain * 100).toFixed(1)} pts</text>`;
  });
  svg.innerHTML = out;
  $("#chartnote").textContent = "gain = verified − baseline, same problems, same student model, 0 regressions in all Arabic runs";
}

function sliceOrder(summary) {
  const fixed = ["all", "math", "logic", "hard", "fragment", "eastern-digits", "relation"].filter((k) => summary[k]);
  const rest = Object.keys(summary).filter((k) => !fixed.includes(k) && k !== "arabic" && summary[k].n >= 5).sort((a, b) => summary[b].n - summary[a].n);
  return [...fixed, ...rest];
}

function problemsTable(run, key, tag) {
  const rows = run.rows.filter((r) => !r.error && (tag === "all" || (r.tags || []).includes(tag)));
  const tr = rows.map((r) => {
    const cls = r.baseline_correct ? (r.final_correct ? "" : "gain-neg") : r.final_correct ? "gain-pos" : "";
    const tracePath = `${run.paths.traces}/${r.id}.json`;
    return `<tr>
      <td><a href="${gh(tracePath)}" target="_blank" rel="noopener" title="assurance trace on GitHub">${esc(r.id)}</a></td>
      <td class="ar" dir="auto">${esc(run.problems[r.id] || "")}</td>
      <td>${esc(r.expected)}</td>
      <td dir="auto">${esc(r.baseline_answer)} ${r.baseline_correct ? "" : '<span class="badge refuted">✗</span>'}</td>
      <td dir="auto" class="${cls}">${esc(r.final_answer)} ${r.final_correct ? '<span class="badge verified">✓</span>' : '<span class="badge refuted">✗</span>'}</td>
      <td>${r.r1_flagged ? '<span class="badge refuted">refuted r1</span>' : '<span class="badge skipped">—</span>'}</td>
      <td>${r.rounds}</td>
      <td><span class="badge ${esc(r.status)}">${esc(r.status)}</span></td>
      <td><a class="evid" href="/api/bench/trace/${encodeURIComponent(key)}/${encodeURIComponent(run.run)}/${encodeURIComponent(r.id)}" target="_blank">json</a>
          <a class="evid" href="/?trace=${encodeURIComponent(key)}/${encodeURIComponent(run.run)}/${encodeURIComponent(r.id)}" title="open in the verifier UI">view</a></td>
    </tr>`;
  }).join("");
  return `<table class="probs"><thead><tr><th>id</th><th>problem</th><th>gold</th><th>baseline (r1)</th><th>final</th><th>Lean r1</th><th>rounds</th><th>status</th><th>trace</th></tr></thead><tbody>${tr}</tbody></table>`;
}

function renderRun(key, run) {
  const s = run.summary;
  const slices = sliceOrder(s);
  const rows = slices.map((sl) => {
    const r = s[sl];
    const g = r.abs_gain;
    const code = CODE_FOR_TAG[sl];
    const lean = LEAN_FOR_TAG[sl];
    return `<tr>
      <td class="slice-name"><b>${esc(sl)}</b></td><td>${r.n}</td>
      <td>${pct(r.baseline_accuracy)}<div class="bar"><i class="base" style="width:${r.baseline_accuracy * 100}%"></i></div></td>
      <td>${pct(r.verified_accuracy)}<div class="bar"><i class="ver" style="width:${r.verified_accuracy * 100}%"></i></div></td>
      <td class="${g > 0 ? "gain-pos" : g < 0 ? "gain-neg" : ""}">${g > 0 ? "+" : ""}${(g * 100).toFixed(1)} pts</td>
      <td>${pct(r.detection_recall)}</td><td>${pct1(r.false_alarm_rate)}</td><td>${pct(r.fix_rate)}</td><td>${r.regressions ?? 0}</td>
      <td>${r.assured_and_correct}/${r.assured_final_answers}</td><td>${r.mean_rounds}</td><td>${r.mean_latency_s}s</td>
      <td><a class="evid" href="#" data-run="${esc(key)}" data-tag="${esc(sl)}">problems ▾</a>
          ${code ? `<a class="evid" href="${gh(code)}" target="_blank" rel="noopener">code</a>` : ""}
          ${lean ? `<a class="evid" href="${gh(lean)}" target="_blank" rel="noopener">Lean</a>` : ""}</td>
    </tr>`;
  }).join("");
  return `<section class="card" style="margin-top:18px" id="run-${esc(key)}">
    <h2 style="margin-top:0">${esc(RUN_LABELS[key] || key)}</h2>
    <div class="runmeta">student <b>${esc(run.student_model)}</b> · formalizer <b>${esc(run.formalizer_model)}</b> · Lean 4 + Mathlib · max rounds ${run.max_rounds} · wall ${Math.round(run.wall_time_s)}s · run <code>${esc(run.run)}</code></div>
    <div class="links">
      <a href="${gh(run.dataset)}" target="_blank" rel="noopener">problems (${esc(run.dataset)})</a>
      <a href="${gh(run.paths.results)}" target="_blank" rel="noopener">results.json</a>
      <a href="${gh(run.paths.traces)}" target="_blank" rel="noopener">all assurance traces</a>
      <a href="${gh("bench/report.py")}" target="_blank" rel="noopener">scoring code</a>
      <a href="${gh("docs/BENCHMARK.md")}" target="_blank" rel="noopener">BENCHMARK.md</a>
    </div>
    <table class="bench" style="margin-top:12px"><thead><tr><th>slice</th><th>n</th><th>baseline acc</th><th>verified acc</th><th>gain</th>
      <th>Lean recall on wrong</th><th>false alarms</th><th>fix rate</th><th>regressions</th><th>assured &amp; correct</th><th>rounds</th><th>latency</th><th>evidence</th></tr></thead>
      <tbody>${rows}</tbody></table>
    <div class="probs-host"></div>
  </section>`;
}

async function init() {
  const data = await (await fetch("/api/bench/runs")).json();
  GH = data.github;
  const runs = data.runs;
  drawChart(runs);
  const order = [...Object.keys(RUN_LABELS).filter((k) => runs[k]), ...Object.keys(runs).filter((k) => !RUN_LABELS[k]).sort()];
  $("#runs").innerHTML = order.map((k) => renderRun(k, runs[k])).join("");
  document.querySelectorAll("a.evid[data-tag]").forEach((a) => {
    a.onclick = (e) => {
      e.preventDefault();
      const host = $(`#run-${CSS.escape(a.dataset.run)} .probs-host`);
      const same = host.dataset.tag === a.dataset.tag && host.innerHTML;
      host.dataset.tag = a.dataset.tag;
      host.innerHTML = same ? "" : `<h3 style="margin-top:14px">problems in slice “${esc(a.dataset.tag)}” — each id links to its assurance trace</h3>` + problemsTable(runs[a.dataset.run], a.dataset.run, a.dataset.tag);
      if (!same) host.scrollIntoView({ behavior: "smooth", block: "nearest" });
    };
  });
  $("#codelinks").innerHTML = [
    ["falconverifier/agent.py", "verify-and-teach loop"],
    ["falconverifier/arabic.py", "Arabic arithmetic pregroup fragment"],
    ["falconverifier/arabic_logic.py", "Arabic quantifier logic fragment"],
    ["falconverifier/arabic_graph.py", "Arabic relation / counting fragment"],
    ["falconverifier/formalizer.py", "LLM formalizer + faithfulness audit"],
    ["falconverifier/lean_runner.py", "Lean 4 runner"],
    ["lean/FalconVerifier", "Lean 4 library (pregroup semantics, graph lemmas)"],
    ["falconverifier/bench.py", "benchmark harness"],
    ["docs/REPORT_falcon3b_arabic.pdf", "academic report (PDF)"],
    ["docs/DPO.md", "Lean-refuted → Lean-verified preference data"],
  ].map(([p, l]) => `<a href="${gh(p)}" target="_blank" rel="noopener">${esc(l)}</a>`).join("");
}
init();
