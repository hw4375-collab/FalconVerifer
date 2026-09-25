const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// [label, problem, expected, English translation (Arabic items)]
const EXAMPLES = [
  ["عربي · ضرب ثم طرح", "اشترى يوسف 81 علبة تحتوي كل منها على 39 زجاجة، ثم أعطى 235 زجاجة من مجموعها لأصدقائه. كم زجاجة بقي لدى يوسف؟", "2924",
    "Yusuf bought 81 boxes with 39 bottles each, then gave 235 bottles to his friends. How many bottles does he have left?"],
  ["عربي · أرقام شرقية", "اشترى راشد ٧٤ علبة تحتوي كل منها على ٤٧ عملة، ثم أعطى ٢٣٦ عملة من مجموعها لأصدقائه. كم عملة بقي لدى راشد؟", "3242",
    "Rashid bought 74 boxes with 47 coins each (Eastern Arabic digits), then gave away 236 coins. How many coins are left?"],
  ["عربي · مجموع وفرق", "احسب مجموع ٨١٢ و ٤٦٥ ناقص ٤٨.", "1229",
    "Compute the sum of 812 and 465 minus 48."],
  ["عربي · خصم مركب", "يبلغ سعر هاتف 800 درهماً. خُفِّض بنسبة 10٪ ثم خُفِّض السعر الجديد بنسبة 20٪ أخرى. ما هو السعر النهائي بالدرهم؟", "576",
    "A phone costs 800 dirhams. It is reduced by 10%, then the new price by another 20%. What is the final price?"],
  ["عربي · ترتيب العمليات", "احسب قيمة ٣٦ + ٩ × ٨ − ٣² باتباع ترتيب العمليات.", "99",
    "Evaluate 36 + 9 × 8 − 3² following the order of operations."],
  ["عربي · منطق", "كل الأطباء متعلمون، وبعض المتعلمين أثرياء. هل يلزم أن بعض الأطباء أثرياء؟ أجب بنعم أو لا.", "لا",
    "All doctors are educated, and some educated people are wealthy. Must some doctors be wealthy? Answer yes or no."],
  ["عربي · شرط", "إذا أمطرت فإن الأرض تبتل. الأرض مبتلة. هل يلزم أنها أمطرت؟ أجب بنعم أو لا.", "لا",
    "If it rains, the ground gets wet. The ground is wet. Must it have rained? Answer yes or no."],
  ["عربي · مصافحة", "خمسة طلاب يجلسون في الفصل، ويقول كل واحد منهم إن ثلاثة من الأربعة الباقين أصدقاؤه. هل يلزم أن أحدهم يكذب؟ أجب بنعم أو لا.", "نعم",
    "Five students sit in class; each says three of the other four are his friends. Must one of them be lying? Answer yes or no. (Handshake lemma: 5×3 is odd.)"],
  ["Muffins", "A bakery makes 48 muffins per batch. It bakes 7 batches and then sells 5 boxes of 12 muffins each. How many muffins are left?", "276"],
  ["Percent", "A jacket costs $120. It is discounted by 25%, then a 10% sales tax is added. What is the final price?", "99"],
  ["Doctors", "All doctors are educated. Some educated people are wealthy. Does it follow that some doctors are wealthy? Answer Yes or No.", "No"],
  ["Ages", "Tom is 3 times as old as Jerry. In 8 years Tom will be twice as old as Jerry. How old is Jerry now?", "8"],
];
const WEAK_STUDENT = "falcon-h1-arabic-3b-instruct";

const state = { rounds: {}, es: null, ctrl: null, t0: 0, timer: null, hardness: {} };

function badge(v) { return `<span class="badge ${v}">${v.replace("_", "-")}</span>`; }

function setStatus(msg, busy = true) {
  const el = $("#status");
  el.classList.remove("hidden");
  el.innerHTML = `${busy ? '<span class="dot"></span>' : ""}<span>${esc(msg)}</span>${busy ? '<span class="elapsed muted"></span>' : ""}`;
}

function roundCard(n) {
  if (state.rounds[n]) return state.rounds[n];
  const tpl = $("#round-tpl").content.cloneNode(true);
  const card = tpl.querySelector("article");
  card.querySelector(".n").textContent = n;
  $("#roundlist").appendChild(card);
  state.rounds[n] = card;
  card.scrollIntoView({ behavior: "smooth", block: "start" });
  return card;
}

function renderAnswer(card, a) {
  const ans = card.querySelector(".answer");
  ans.innerHTML = esc(a.raw);
  ans.dir = /[\u0600-\u06FF]/.test(a.raw) ? "rtl" : "ltr";
  if (a.reasoning) {
    const d = card.querySelector(".cot");
    d.classList.remove("hidden");
    d.querySelector("pre").textContent = a.reasoning;
  }
  card.dataset.steps = JSON.stringify(a.steps);
}

function renderFormalization(card, f) {
  const steps = JSON.parse(card.dataset.steps || "[]");
  const byIdx = Object.fromEntries(f.steps.map((s) => [s.index, s]));
  const rows = steps.map((s) => {
    const fs = byIdx[s.index];
    const grammar = fs && fs.note && fs.note.startsWith("pregroup:")
      ? `<div class="muted pregroup" title="deterministic pregroup-grammar translation (no LLM)">${esc(fs.note)}</div>`
      : "";
    return `<tr data-idx="${s.index}"><td>${s.index}</td><td dir="auto">${esc(s.text)}</td>
      <td><code>${fs && fs.lean_prop ? esc(fs.lean_prop) : `<span class="muted">${esc(fs?.note || "skip")}</span>`}</code>${grammar}</td>
      <td class="verdict"><span class="muted">Lean…</span></td></tr>`;
  });
  const problemGrammar = f.problem_note && f.problem_note.startsWith("pregroup:")
    ? `<div class="muted pregroup" title="deterministic grammar translation of the question (no LLM); ≡ marks lemma identifications across morphological variants">${esc(f.problem_note)}</div>`
    : "";
  rows.push(`<tr data-idx="final"><td>final</td><td class="muted">final answer follows from the problem</td>
    <td><code>${f.problem_prop ? esc(f.problem_prop) : '<span class="muted">—</span>'}</code>${problemGrammar}</td><td class="verdict"><span class="muted">Lean…</span></td></tr>`);
  card.querySelector("tbody").innerHTML = rows.join("");
}

const VERDICTS = ["verified", "refuted", "unknown", "ill_formed", "skipped"];

function renderCotBar(card, rep) {
  const all = [...rep.steps.map((s) => s.verdict), rep.final_answer_verdict];
  const n = all.length;
  const bar = card.querySelector(".cotbar");
  const counts = Object.fromEntries(VERDICTS.map((v) => [v, all.filter((x) => x === v).length]));
  bar.classList.remove("hidden");
  bar.querySelector(".seg").innerHTML = VERDICTS.filter((v) => counts[v])
    .map((v) => `<i class="${v}" style="flex:${counts[v]}" title="${counts[v]} ${v}"></i>`).join("");
  const decided = counts.verified + counts.refuted;
  bar.querySelector(".sum").innerHTML = `CoT verifiability: Lean decided <b>${decided}/${n}</b> claims (steps + final) · `
    + VERDICTS.filter((v) => counts[v]).map((v) => `${counts[v]} ${v.replace("_", "-")}`).join(" · ");
}

function renderReport(card, rep) {
  renderCotBar(card, rep);
  for (const s of rep.steps) {
    const tr = card.querySelector(`tr[data-idx="${s.index}"]`);
    if (!tr) continue;
    tr.querySelector(".verdict").innerHTML = badge(s.verdict) + (s.detail ? `<div class="muted" style="font-size:11px;margin-top:4px">${esc(s.detail.slice(0, 160))}</div>` : "");
    if (s.verdict === "refuted") tr.style.background = "rgba(255,92,122,.07)";
    if (s.lean_prop && !tr.querySelector("code").textContent.trim()) tr.querySelector("code").textContent = s.lean_prop;
  }
  const fr = card.querySelector('tr[data-idx="final"] .verdict');
  if (fr && rep.final_answer_verdict === "refuted") fr.closest("tr").style.background = "rgba(255,92,122,.07)";
  if (fr) fr.innerHTML = badge(rep.final_answer_verdict) + (rep.final_answer_detail ? `<div class="muted" style="font-size:11px;margin-top:4px">${esc(rep.final_answer_detail.slice(0, 160))}</div>` : "");
  const h = card.querySelector(".col:last-child h3");
  h.textContent = `2 · Formalized to Lean 4 → 3 · Lean kernel verdict (${rep.lean_latency_s.toFixed(1)}s)`;
  if (rep.lean_file) {
    const d = card.querySelector(".leansrc");
    d.classList.remove("hidden");
    d.querySelector("pre").textContent = rep.lean_file;
  }
}

function renderFeedback(card, fb) {
  const d = card.querySelector(".feedback");
  d.classList.remove("hidden");
  const pre = d.querySelector("pre");
  pre.textContent = fb;
  pre.dir = /[\u0600-\u06FF]/.test(fb) ? "rtl" : "ltr";
}

function renderResult(t) {
  const el = $("#result");
  el.classList.remove("hidden");
  const exp = t.expected_answer ? `<div class="kpi"><div class="muted">expected</div><div class="v" dir="auto">${esc(t.expected_answer)}</div></div>` : "";
  const steps = t.rounds.flatMap((r) => [...r.report.steps.map((s) => s.verdict), r.report.final_answer_verdict]);
  const decided = steps.filter((v) => v === "verified" || v === "refuted").length;
  const refuted = steps.filter((v) => v === "refuted").length;
  const last = t.rounds[t.rounds.length - 1].report;
  const open = last.steps.filter((s) => s.verdict === "unknown" || s.verdict === "ill_formed").length;
  const story = t.rounds.length > 1 && t.status === "verified"
    ? `round 1 refuted → taught → round ${t.rounds.length} verified`
    : t.status !== "verified" ? `ended ${t.status}`
      : open ? `final answer proved in round 1 · ${open} step${open > 1 ? "s" : ""} left unknown`
        : "final answer and every checkable step proved in round 1";
  el.innerHTML = `
    <div class="kpi"><div class="muted">status</div><div class="v ${t.status}">${t.status}</div><div class="sub muted">${story}</div></div>
    <div class="kpi"><div class="muted">final answer</div><div class="v" dir="auto">${esc(t.final_answer ?? "—")}</div></div>
    <div class="kpi"><div class="muted">assurance score</div><div class="v">${(t.assurance_score * 100).toFixed(0)}%</div><div class="sub muted">last round: ½ verified share of checkable steps + ½ final-answer verdict</div></div>
    <div class="kpi"><div class="muted">claims decided by Lean</div><div class="v">${decided}/${steps.length}</div><div class="sub muted">all rounds, steps + final · ${refuted} refuted · ${steps.length - decided} unknown/skipped</div></div>
    <div class="kpi"><div class="muted">rounds · time</div><div class="v">${t.rounds.length} · ${t.total_latency_s}s</div></div>${exp}
    <div class="kpi"><div class="muted">evidence</div><div class="v"><a id="dl" download="assurance_trace.json">download trace</a></div><div class="sub muted">full JSON: answers, Lean claims, verdicts, feedback, kernel source</div></div>`;
  $("#dl").href = URL.createObjectURL(new Blob([JSON.stringify(t, null, 1)], { type: "application/json" }));
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function run(baselineOnly = false) {
  const problem = $("#problem").value.trim();
  if (!problem) return;
  state.rounds = {};
  $("#roundlist").innerHTML = "";
  $("#result").classList.add("hidden");
  if (location.search) history.replaceState(null, "", location.pathname);
  $("#run").disabled = $("#baseline").disabled = true;
  $("#stop").classList.remove("hidden");
  state.t0 = Date.now();
  clearInterval(state.timer);
  state.timer = setInterval(() => { const e = $("#status .elapsed"); if (e) e.textContent = `${((Date.now() - state.t0) / 1000).toFixed(0)}s`; }, 500);
  setStatus("asking Falcon…");
  const body = {
    problem,
    expected: $("#expected").value.trim() || null,
    rounds: baselineOnly ? 1 : Number($("#rounds").value),
    formalizer: $("#formalizer").value,
    student_model: $("#student").value || null,
  };
  state.ctrl = new AbortController();
  try {
    const headers = { "Content-Type": "application/json" };
    const token = localStorage.getItem("fv_token");
    if (token) headers["X-FV-Token"] = token;
    const res = await fetch("/api/solve/stream", {
      method: "POST", headers, body: JSON.stringify(body), signal: state.ctrl.signal,
    });
    if (!res.ok) {
      let msg = res.statusText;
      try { msg = (await res.json()).detail || msg; } catch (_) { /* not json */ }
      if (res.status === 401) {
        const t = prompt("This deployment requires an access token:");
        if (t) { localStorage.setItem("fv_token", t); return run(baselineOnly); }
      }
      throw new Error(`${res.status}: ${msg}`);
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        const ev = /^event: (.*)$/m.exec(chunk)?.[1];
        const data = /^data: (.*)$/m.exec(chunk)?.[1];
        if (ev && data) handle(ev, JSON.parse(data));
      }
    }
  } catch (e) {
    if (e.name !== "AbortError") setStatus("error: " + e.message, false);
    else setStatus("stopped", false);
  } finally {
    clearInterval(state.timer);
    $("#stop").classList.add("hidden");
    $("#run").disabled = $("#baseline").disabled = false;
  }
}

function handle(kind, p) {
  switch (kind) {
    case "config": $("#cfg").innerHTML = `student <b>${esc(p.student)}</b><br>formalizer <b>${esc(p.formalizer)}</b> · kernel <b>Lean 4 + Mathlib</b>`; break;
    case "round_start": roundCard(p.round); setStatus(`round ${p.round}/${p.max_rounds}: Falcon is answering…`); break;
    case "student_answer": renderAnswer(roundCard(p.round), p.answer); setStatus(`round ${p.round}: translating steps to Lean 4…`); break;
    case "formalized": renderFormalization(roundCard(p.round), p.formalization); setStatus(`round ${p.round}: Lean 4 kernel is checking…`); break;
    case "repair": setStatus(`round ${p.round}: repairing ill-formed Lean claims…`); break;
    case "audit_discard": setStatus(`round ${p.round ?? ""}: refutation of step ${p.step} discarded after faithfulness audit`); break;
    case "verified": renderReport(roundCard(p.round), p.report); break;
    case "feedback": renderFeedback(roundCard(p.round), p.feedback); setStatus(`round ${p.round}: teaching Falcon what Lean refuted…`); break;
    case "done": renderResult(p.trace); setStatus(`done — ${p.trace.status} in ${p.trace.total_latency_s}s`, false); break;
    case "status": setStatus(p.message); break;
    case "saved": break;
    case "error": setStatus("error: " + p.message, false); break;
  }
}

function pct(x) { return x == null ? "–" : (x * 100).toFixed(0) + "%"; }

async function loadBench() {
  const data = await (await fetch("/api/bench/latest")).json();
  const headline = ["falcon3b_arabic", "falcon3b_arabic_scale", "falcon7b_arabic"].filter((k) => data[k]);
  const keys = headline.length ? headline : Object.keys(data);
  if (!keys.length) return;
  const parts = keys.map((k) => {
    const s = data[k].summary;
    const slices = ["all", "math", "logic"].filter((x) => s[x]);
    const rows = slices.map((sl) => {
      const r = s[sl];
      const g = r.abs_gain;
      return `<tr><td>${sl}</td><td>${r.n}</td>
        <td>${pct(r.baseline_accuracy)}<div class="bar"><i class="base" style="width:${r.baseline_accuracy * 100}%"></i></div></td>
        <td>${pct(r.verified_accuracy)}<div class="bar"><i class="ver" style="width:${r.verified_accuracy * 100}%"></i></div></td>
        <td class="${g > 0 ? "gain-pos" : g < 0 ? "gain-neg" : ""}">${g > 0 ? "+" : ""}${(g * 100).toFixed(1)} pts</td>
        <td>${pct(r.detection_recall)}</td><td>${pct(r.false_alarm_rate)}</td><td>${pct(r.fix_rate)}</td>
        <td>${r.assured_and_correct}/${r.assured_final_answers}</td><td>${r.mean_rounds}</td><td>${r.mean_latency_s}s</td></tr>`;
    }).join("");
    return `<h3 style="margin-top:14px">${esc(k)} <span class="muted">(${esc(data[k].run)})</span></h3>
      <table class="bench"><thead><tr><th>slice</th><th>n</th><th>baseline acc</th><th>verified acc</th><th>gain</th>
      <th>Lean recall on wrong</th><th>false alarms</th><th>fix rate</th><th>assured &amp; correct</th><th>rounds</th><th>latency</th></tr></thead><tbody>${rows}</tbody></table>`;
  });
  $("#bench").innerHTML = parts.join("");
}

function hardnessBadge(text) {
  const h = state.hardness[text];
  if (!h || !h.total) return "";
  const cls = h.wrong === h.total ? "hard" : h.wrong ? "mid" : "easy";
  return `<span class="hb ${cls}" title="Falcon 3B Arabic answered round 1 wrong in ${h.wrong} of ${h.total} benchmark runs">3B ✗ ${h.wrong}/${h.total}</span>`;
}

function renderExamples() {
  const ex = $("#examples");
  ex.innerHTML = "";
  for (const [name, text, expected, translation] of EXAMPLES) {
    const b = document.createElement("button");
    b.innerHTML = `${esc(name)} ${hardnessBadge(text)}`;
    if (translation) b.title = translation;
    b.onclick = () => {
      $("#problem").value = text;
      $("#expected").value = expected;
      $("#translation").textContent = translation ? `English: ${translation}` : "";
      if (translation) $("#student").value = WEAK_STUDENT;
    };
    ex.appendChild(b);
  }
}

async function loadReplays() {
  const el = $("#replaylist");
  try {
    const data = await (await fetch("/api/bench/runs")).json();
    const run = data.runs.falcon3b_arabic;
    if (!run) { $("#replays").classList.add("hidden"); return; }
    const wrong = run.rows.filter((r) => !r.error && !r.baseline_correct);
    const short = (r) => r.baseline_answer && r.baseline_answer.length <= 14 && String(r.final_answer).length <= 14;
    const pool = wrong.filter((r) => r.final_correct && r.status === "verified" && short(r))
      .sort((a, b) => a.rounds - b.rounds || a.id.localeCompare(b.id));
    const fixed = [...pool.filter((r) => r.id.startsWith("armath")).slice(0, 3), ...pool.filter((r) => !r.id.startsWith("armath")).slice(0, 3)];
    el.classList.remove("muted");
    el.innerHTML = fixed.map((r) => `<a class="replay" href="/?trace=falcon3b_arabic/${run.run}/${r.id}">
        <span class="ar" dir="rtl">${esc(run.problems[r.id])}</span>
        <span class="meta"><span class="badge refuted">R1 ${esc(r.baseline_answer)}</span> → <span class="badge verified">R${r.rounds} ${esc(r.final_answer)}</span> · gold ${esc(r.expected)}</span></a>`).join("")
      + `<div class="muted small">${fixed.length} of the ${wrong.length} round-1 errors in the latest ${run.rows.length}-problem run, caught and fixed by Lean feedback — <a href="/benchmark">all of them, with evidence →</a></div>`;
  } catch { el.textContent = "benchmark traces unavailable"; }
}

async function init() {
  renderExamples();
  $("#run").onclick = () => run(false);
  $("#baseline").onclick = () => run(true);
  $("#stop").onclick = () => state.ctrl && state.ctrl.abort();
  $("#problem").addEventListener("input", () => { $("#translation").textContent = ""; });
  fetch("/api/bench/hardness").then((r) => r.json()).then((h) => { state.hardness = h; renderExamples(); }).catch(() => {});
  loadReplays();
  try {
    const c = await (await fetch("/api/config")).json();
    $("#cfg").innerHTML = `student <b>${esc(c.student)}</b><br>formalizer <b>${esc(c.formalizer)}</b> · kernel <b>Lean 4 + Mathlib</b>`;
    $("#formalizer").value = c.formalizer_provider;
    for (const opt of $("#formalizer").options) {
      if (c.providers[opt.value] && !c.providers[opt.value].configured) { opt.disabled = true; opt.textContent += " (no key)"; }
    }
    $("#rounds").value = c.max_rounds;
  } catch {}
  loadBench();
  const ref = new URLSearchParams(location.search).get("trace");
  if (ref) replayTrace(ref);
}

// Replay a committed benchmark trace through the same renderers the live loop uses.
async function replayTrace(ref) {
  const res = await fetch("/api/bench/trace/" + ref.split("/").map(encodeURIComponent).join("/"));
  if (!res.ok) { setStatus(`trace ${ref} not found`, false); return; }
  const t = await res.json();
  $("#problem").value = t.problem;
  $("#expected").value = t.expected_answer ?? "";
  const ex = EXAMPLES.find((e) => e[1] === t.problem);
  $("#translation").textContent = ex && ex[3] ? `English: ${ex[3]}` : "";
  if (t.student_model) $("#student").value = t.student_model;
  $("#roundlist").innerHTML = "";
  state.rounds = {};
  setStatus(`replaying benchmark trace ${ref} · student ${t.student_model} · formalizer ${t.formalizer_model}`, false);
  t.rounds.forEach((r, i) => {
    const card = roundCard(i + 1);
    renderAnswer(card, r.answer);
    renderFormalization(card, r.formalization);
    renderReport(card, r.report);
    if (r.feedback) renderFeedback(card, r.feedback);
  });
  renderResult(t);
  $("#status").scrollIntoView({ behavior: "smooth", block: "start" });
}
init();
