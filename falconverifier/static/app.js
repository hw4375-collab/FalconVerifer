const $ = (s, el = document) => el.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const EXAMPLES = [
  ["Muffins", "A bakery makes 48 muffins per batch. It bakes 7 batches and then sells 5 boxes of 12 muffins each. How many muffins are left?", "276"],
  ["Percent", "A jacket costs $120. It is discounted by 25%, then a 10% sales tax is added. What is the final price?", "99"],
  ["Doctors", "All doctors are educated. Some educated people are wealthy. Does it follow that some doctors are wealthy? Answer Yes or No.", "No"],
  ["Rain", "If it rains, the street is wet. The street is wet. Does it follow that it rained? Answer Yes or No.", "No"],
  ["Ages", "Tom is 3 times as old as Jerry. In 8 years Tom will be twice as old as Jerry. How old is Jerry now?", "8"],
  ["Divisible", "Is 7 * 12 + 5 divisible by 3? Answer Yes or No.", "No"],
  ["عربي · حساب", "ما هو ناتج ١٧ × ٢٣؟", "391"],
  ["عربي · نسبة", "سعر حقيبة ١٢٠ درهماً. خُفّض السعر بنسبة ٢٥٪ ثم أُضيفت ضريبة ١٠٪. ما السعر النهائي؟", "99"],
  ["عربي · صعب", "يبلغ سعر هاتف 800 درهماً. خُفِّض بنسبة 10٪ ثم خُفِّض السعر الجديد بنسبة 20٪ أخرى. ما هو السعر النهائي بالدرهم؟", "576"],
  ["عربي · ترتيب العمليات", "احسب قيمة ٣٦ + ٩ × ٨ − ٣² باتباع ترتيب العمليات.", "99"],
  ["عربي · منطق", "كل الأطباء متعلمون، وبعض المتعلمين أثرياء. هل يلزم أن بعض الأطباء أثرياء؟ أجب بنعم أو لا.", "لا"],
  ["عربي · شرط", "إذا أمطرت فإن الأرض تبتل. الأرض مبتلة. هل يلزم أنها أمطرت؟ أجب بنعم أو لا.", "لا"],
];

const state = { rounds: {}, es: null, ctrl: null };

function badge(v) { return `<span class="badge ${v}">${v.replace("_", "-")}</span>`; }

function setStatus(msg, busy = true) {
  const el = $("#status");
  el.classList.remove("hidden");
  el.innerHTML = `${busy ? '<span class="dot"></span>' : ""}<span>${esc(msg)}</span>`;
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

function renderReport(card, rep) {
  for (const s of rep.steps) {
    const tr = card.querySelector(`tr[data-idx="${s.index}"]`);
    if (!tr) continue;
    tr.querySelector(".verdict").innerHTML = badge(s.verdict) + (s.detail ? `<div class="muted" style="font-size:11px;margin-top:4px">${esc(s.detail.slice(0, 160))}</div>` : "");
    if (s.verdict === "refuted") tr.style.background = "rgba(255,92,122,.07)";
    if (s.lean_prop && !tr.querySelector("code").textContent.trim()) tr.querySelector("code").textContent = s.lean_prop;
  }
  const fr = card.querySelector('tr[data-idx="final"] .verdict');
  if (fr) fr.innerHTML = badge(rep.final_answer_verdict) + (rep.final_answer_detail ? `<div class="muted" style="font-size:11px;margin-top:4px">${esc(rep.final_answer_detail.slice(0, 160))}</div>` : "");
  const h = card.querySelector(".col:last-child h3");
  h.textContent = `2 · Formalized to Lean 4 → 3 · Lean kernel verdict (${rep.lean_latency_s.toFixed(1)}s)`;
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
  const exp = t.expected_answer ? `<div class="kpi"><div class="muted">expected</div><div class="v">${esc(t.expected_answer)}</div></div>` : "";
  el.innerHTML = `
    <div class="kpi"><div class="muted">status</div><div class="v ${t.status}">${t.status}</div></div>
    <div class="kpi"><div class="muted">final answer</div><div class="v">${esc(t.final_answer ?? "—")}</div></div>
    <div class="kpi"><div class="muted">assurance score</div><div class="v">${(t.assurance_score * 100).toFixed(0)}%</div></div>
    <div class="kpi"><div class="muted">rounds · time</div><div class="v">${t.rounds.length} · ${t.total_latency_s}s</div></div>${exp}`;
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function run(baselineOnly = false) {
  const problem = $("#problem").value.trim();
  if (!problem) return;
  state.rounds = {};
  $("#roundlist").innerHTML = "";
  $("#result").classList.add("hidden");
  $("#run").disabled = $("#baseline").disabled = true;
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
  } finally {
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
  const keys = Object.keys(data);
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

async function init() {
  const ex = $("#examples");
  for (const [name, text, expected] of EXAMPLES) {
    const b = document.createElement("button");
    b.textContent = name;
    b.onclick = () => { $("#problem").value = text; $("#expected").value = expected; };
    ex.appendChild(b);
  }
  $("#run").onclick = () => run(false);
  $("#baseline").onclick = () => run(true);
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
}
init();
