import { el, loadConfig, buildScale, zoneFor, zoneColor, reduceMotion, gsap, formatTime } from "./common.js";
import { initChrome, magnetic } from "./effects.js";

const $ = (id) => document.getElementById(id);
const HIST_KEY = "cp_history_v1";

const STAGES = [
  { key: "credit_systemic", label: "Credit and systemic" },
  { key: "liquidity_shock", label: "Liquidity and shock" },
  { key: "macro", label: "Macro" },
  { key: "geopolitical", label: "News and geopolitics" },
  { key: "summary", label: "Writing the summary" },
];

let config = null;
let running = false;
let current = null; // the result being shown
let currentId = null;
let chatBusy = false;
let chatLog = []; // questions and answers of the analysis being shown, saved with it for this visit

/* ---------------------------------------------------------------- history (this visit only) */
// History lives in sessionStorage: it survives a page refresh but is cleared when the tab is closed, so every new
// visit starts empty and nobody ever sees another visitor's analyses.
try { localStorage.removeItem(HIST_KEY); } catch { /* older versions kept history for good; remove it */ }
function readHistory() {
  try { return JSON.parse(sessionStorage.getItem(HIST_KEY) || "[]"); } catch { return []; }
}
function writeHistory(list) {
  try { sessionStorage.setItem(HIST_KEY, JSON.stringify(list.slice(0, 10))); } catch { /* storage unavailable */ }
}
function saveHistory(result) {
  const id = `${Date.now()}`;
  writeHistory([{ id, result, chat: [] }, ...readHistory()]);
  return id;
}
function saveChat(id, chat) {
  const list = readHistory();
  const entry = list.find((e) => e.id === id);
  if (entry) { entry.chat = chat.slice(-20); writeHistory(list); }
}
function renderHistory() {
  const host = $("hist");
  const list = readHistory();
  host.textContent = "";
  $("clear-hist").hidden = list.length === 0;
  if (!list.length) host.append(el("p", { class: "muted small", text: "No analyses yet." }));
  list.forEach(({ id, result, chat }) => {
    const asked = chat ? chat.length : 0;
    const zone = zoneFor(result.composite, config.regimes);
    const b = el("button", { type: "button", class: id === currentId ? "current" : "" },
      el("b", { text: result.composite.toFixed(1) }),
      el("span", { text: `${zone.label}, alarm ${result.status === "ON" ? "on" : "off"}` }),
      el("small", { text: formatTime(result.created_at) + (asked ? ` · ${asked} question${asked > 1 ? "s" : ""}` : "") }));
    b.addEventListener("click", () => {
      if (running) return;
      currentId = id;
      showResult(result, { animate: false, fromHistory: true, chat: chat || [] });
    });
    host.append(b);
  });
}

/* ---------------------------------------------------------------- views */
function showView(name) {
  $("view-idle").hidden = name !== "idle";
  $("view-run").hidden = name !== "run";
  $("view-answer").hidden = name !== "answer";
}
function showError(msg) {
  const box = $("error");
  box.textContent = msg;
  box.hidden = !msg;
}
function resetResult() {
  ["drivers", "followup", "disclaimer"].forEach((id) => ($(id).hidden = true));
  $("signals-panel").hidden = true;
  $("pair").hidden = true;
  $("groups").textContent = "";
  $("msgs").textContent = "";
  chatLog = [];
  $("news-callout").hidden = true;
}

/* ---------------------------------------------------------------- stage chips */
function buildStages() {
  const host = $("stages");
  host.textContent = "";
  return STAGES.map((s) => {
    const chip = el("span", { class: "stage" }, el("i"), s.label);
    host.append(chip);
    return chip;
  });
}
const STATUS_TEXT = [
  "Reading the yield curve, credit spreads, bank stocks, repo rates and the money supply, then scoring each one against history.",
  "Checking the VIX, how far the S&P 500 is below its high, gold and the US dollar.",
  "Looking at jobless claims, inflation and oil prices.",
  "Searching today's news on tariffs and conflict, then scoring what it finds.",
  "Writing a short summary of the result.",
];
function setStages(chips, doneCount) {
  chips.forEach((c, i) => {
    c.classList.toggle("done", i < doneCount);
    c.classList.toggle("active", i === doneCount);
  });
  const line = $("status-line");
  if (line) line.textContent = STATUS_TEXT[Math.min(doneCount, STATUS_TEXT.length - 1)];
}

/* ---------------------------------------------------------------- factor rows */
function factorRow(f) {
  const s = f.score ?? 0;
  const cls = s > 0 ? "pos" : s < 0 ? "neg" : "zero";
  const bar = el("div", { class: "diverge", "aria-hidden": "true" }, s === 0 ? null : el("i", { class: s < 0 ? "neg" : "pos", style: `width:${Math.abs(s) * 5}%` }));
  const row = el("div", { class: "factor", role: "button", tabindex: "0", "aria-expanded": "false" },
    el("div", {},
      el("div", { class: "f-name", text: f.label }),
      el("div", { class: "f-val", text: f.value || "" }),
      el("div", { class: "f-why", text: f.reasoning || "No reason recorded." })),
    bar,
    el("div", { class: `f-score ${cls}`, text: s > 0 ? `+${s}` : String(s) }));
  const toggle = () => {
    const open = row.classList.toggle("open");
    row.setAttribute("aria-expanded", String(open));
  };
  row.addEventListener("click", toggle);
  row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
  return row;
}

function groupBlock(catKey) {
  let g = document.getElementById(`group-${catKey}`);
  if (g) return g.querySelector(".rows");
  const cat = config.categories.find((c) => c.key === catKey);
  g = el("div", { class: "group", id: `group-${catKey}` },
    el("h3", {}, cat.label, el("span", { text: `${cat.weight}% of the score` })),
    el("div", { class: "rows" }));
  $("groups").append(g);
  return g.querySelector(".rows");
}

function addFactors(catKey, factors, animate) {
  $("signals-panel").hidden = false;
  const rows = groupBlock(catKey);
  const cat = config.categories.find((c) => c.key === catKey);
  const made = cat.factors.filter((f) => factors[f.key]).map((f) => {
    const row = factorRow(factors[f.key]);
    rows.append(row);
    return row;
  });
  if (!animate || reduceMotion || !gsap) return;
  gsap.from(made, { opacity: 0, y: 16, duration: 0.7, ease: "power3.out", stagger: 0.07 });
  made.forEach((row, i) => {
    const fill = row.querySelector(".diverge i");
    if (fill) gsap.from(fill, { scaleX: 0, duration: 0.9, ease: "power3.out", delay: 0.2 + i * 0.07 });
  });
}

/* ---------------------------------------------------------------- the answer */
function setScoreText(v) {
  $("score-val").textContent = v.toFixed(1);
}

function newsCalloutText(result) {
  const a = result.news_alert;
  if (!a) return null;
  if (a.level === "moderate") return { cls: "", title: "News alert: moderate", body: "Headlines are somewhat negative. Keep an eye on them, but they are not driving the score on their own." };
  const topics = a.topics.join(" and ");
  const state = result.status === "ON"
    ? "and the market signals are also under strain."
    : "while the overall score is still below the alarm line.";
  return {
    cls: "high", title: "News alert: high",
    body: `Headlines on ${topics} are very negative, ${state} Keep an eye on the market signals: if the VIX rises above 25, the S&P 500 falls more than 5% from its high, or the credit spread widens above 2%, the Crisis Score will rise and the alarm can turn on.`,
  };
}

function showResult(result, { animate, fromHistory = false, chat = [] }) {
  current = result;
  showError("");
  showView("answer");
  const composite = result.composite;
  const zone = zoneFor(composite, config.regimes);

  // score + scale
  const sn = $("score-num");
  sn.textContent = "";
  sn.append(el("span", { id: "score-val", text: animate && !reduceMotion ? "0.0" : composite.toFixed(1) }), el("span", { class: "score-of", text: "/ 100" }));
  const host = $("result-scale");
  const { field } = buildScale(host, config.regimes, { height: 84 });
  const needle = el("div", { class: "needle", style: `height:${84 + 20}px;top:-10px;left:${animate && !reduceMotion ? 0 : composite}%` });
  const label = el("div", { class: "needle-label", text: animate && !reduceMotion ? "0.0" : composite.toFixed(1) });
  needle.append(label);
  host.append(needle);

  // chips and meta
  const chips = $("chips");
  chips.textContent = "";
  const levelChip = el("span", { class: "chip level", style: `background:${zoneColor(zone.label)};${zone.label === "Elevated" ? "color:var(--ink)" : ""}`, text: zone.label });
  const alarmChip = el("span", { class: `chip ${result.status === "ON" ? "on" : ""}` }, el("i"), result.status === "ON" ? "Alarm on" : "Alarm off");
  chips.append(levelChip, alarmChip);
  $("meta-line").textContent = `Confidence: ${result.confidence}. ${formatTime(result.created_at)}.`;

  // news alert and narrative
  const nc = newsCalloutText(result);
  const callout = $("news-callout");
  callout.hidden = !nc;
  if (nc) {
    callout.className = `callout ${nc.cls}`;
    callout.textContent = "";
    callout.append(el("b", { text: nc.title }), el("p", { text: nc.body }));
  }
  $("narrative").textContent = result.narrative || "";

  // drivers
  const rows = $("cat-rows");
  rows.textContent = "";
  const fills = [];
  result.categories.forEach((c) => {
    const fill = el("i", { style: `width:${animate && !reduceMotion ? 0 : c.crisis_pct}%` });
    fills.push([fill, c.crisis_pct]);
    rows.append(el("div", { class: "cat-row" },
      el("div", { class: "name" }, c.label, el("span", { text: `weight ${c.weight}%` })),
      el("div", { class: "track", "aria-label": `${c.label} worry level ${c.crisis_pct} out of 100` }, fill),
      el("div", { class: "pts" }, c.points.toFixed(1), el("small", { text: " pts" }))));
  });
  $("drivers").hidden = false;

  // signals (rows already exist after a live run; rebuild when loading from history)
  $("signals-panel").hidden = false;
  if (fromHistory || !$("groups").children.length) {
    $("groups").textContent = "";
    result.categories.forEach((c) => addFactors(c.key, c.factors, false));
  }
  const fillList = (id, items) => {
    const ul = $(id);
    ul.textContent = "";
    items.forEach((t) => ul.append(el("li", { text: t })));
  };
  fillList("bull-list", result.bullish);
  fillList("bear-list", result.bearish);
  $("pair").hidden = !(result.bullish.length || result.bearish.length);

  $("followup").hidden = false;
  $("disclaimer").hidden = false;
  chatLog = chat.slice();
  const msgs = $("msgs");
  msgs.textContent = "";
  chatLog.forEach((m) => msgs.append(el("div", { class: "msg q", text: m.q }), el("div", { class: "msg a", text: m.a })));
  renderSuggestions();
  window.scrollTo({ top: 0, behavior: "auto" });

  if (animate && !reduceMotion && gsap) {
    const obj = { v: 0 };
    gsap.to(obj, {
      v: composite, duration: 1.8, ease: "power3.out",
      onUpdate: () => { setScoreText(obj.v); label.textContent = obj.v.toFixed(1); },
    });
    gsap.to(needle, { left: `${composite}%`, duration: 1.8, ease: "power3.out" });
    gsap.from([levelChip, alarmChip], { opacity: 0, y: 10, duration: 0.6, ease: "power3.out", delay: 1.4, stagger: 0.12 });
    gsap.from(["#narrative", "#news-callout"], { opacity: 0, y: 14, duration: 0.8, ease: "power3.out", delay: 1.6, stagger: 0.12 });
    fills.forEach(([fill, pct], i) => gsap.to(fill, { width: `${pct}%`, duration: 1.2, ease: "power3.out", delay: 0.5 + i * 0.12 }));
  }
  renderHistory();
}

/* ---------------------------------------------------------------- running an analysis */
async function startAnalysis() {
  if (running) return;
  running = true;
  $("run").disabled = true;
  showError("");
  resetResult();
  current = null;
  currentId = null;
  const chips = buildStages();
  setStages(chips, 0);
  $("bar").style.width = "4%";
  showView("run");
  window.scrollTo({ top: 0, behavior: "auto" });

  const nodeIndex = { credit_systemic: 1, liquidity_shock: 2, macro: 3, geopolitical: 4 };
  let finished = false;
  try {
    const res = await fetch("/api/analyze", { method: "POST", headers: { Accept: "text/event-stream" } });
    if (!res.ok) {
      let msg = "Something went wrong. Please try again.";
      try { msg = (await res.json()).error || msg; } catch { /* keep default */ }
      throw new Error(msg);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let cut;
      while ((cut = buf.indexOf("\n\n")) !== -1) {
        const chunk = buf.slice(0, cut);
        buf = buf.slice(cut + 2);
        const line = chunk.split("\n").find((l) => l.startsWith("data: "));
        if (!line) continue;
        const ev = JSON.parse(line.slice(6));
        if (ev.type === "node") {
          $("bar").style.width = `${Math.max(4, ev.progress * 100)}%`;
          if (ev.category) {
            addFactors(ev.category, ev.factors, true);
            setStages(chips, nodeIndex[ev.category]);
          } else {
            setStages(chips, STAGES.length);
          }
        } else if (ev.type === "result") {
          finished = true;
          currentId = saveHistory(ev.result);
          showResult(ev.result, { animate: true });
        } else if (ev.type === "error") {
          throw new Error(ev.message);
        }
      }
    }
    if (!finished) throw new Error("The analysis ended early. Please try again.");
  } catch (err) {
    const dropped = err instanceof TypeError; // fetch reports a dropped connection as a TypeError
    showError(dropped ? "The connection was interrupted before the analysis finished. Please run it again." : err.message || "Something went wrong. Please try again.");
    $("groups").textContent = "";
    $("signals-panel").hidden = true;
    showView("idle");
  } finally {
    running = false;
    $("run").disabled = false;
  }
}

/* ---------------------------------------------------------------- follow-up chat */
function chatContext() {
  const r = current;
  const lines = [`Crisis Score ${r.composite} out of 100, level ${r.regime}. Alarm ${r.status}. Confidence ${r.confidence}.`, `Summary: ${r.narrative}`, "Signals:"];
  r.categories.forEach((c) => Object.values(c.factors).forEach((f) => lines.push(`- ${f.label}: score ${f.score}. ${f.value}`)));
  return lines.join("\n").slice(0, 5800);
}

const SUGGESTIONS = ["What is this project about?", "Why is the score where it is?", "How was it tested?", "What are its biggest limits?", "What does the alarm mean?"];
function renderSuggestions() {
  const host = $("suggest");
  host.textContent = "";
  if (chatLog.length) return;
  SUGGESTIONS.forEach((q) => {
    const b = el("button", { type: "button", text: q });
    b.addEventListener("click", () => ask(q));
    host.append(b);
  });
}

async function requestAnswer(question) {
  const history = chatLog.slice(-4).flatMap((m) => [{ role: "user", content: m.q }, { role: "assistant", content: m.a }]);
  let lastError = new Error("Could not answer right now. Please try again.");
  for (let attempt = 0; attempt < 2; attempt++) { // one automatic retry for a failed or empty reply
    try {
      const res = await fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, context: chatContext(), history }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.answer) return data.answer;
      lastError = new Error(data.error || (data.detail ? "Please ask a longer question." : "Could not answer right now. Please try again."));
      if (res.status === 429 || res.status === 422) break; // retrying will not help
    } catch (err) {
      lastError = new Error("The connection was interrupted. Please try again.");
    }
  }
  throw lastError;
}

async function ask(question) {
  if (!current || chatBusy) return;
  chatBusy = true;
  $("ask-btn").disabled = true;
  $("suggest").textContent = "";
  const msgs = $("msgs");
  msgs.append(el("div", { class: "msg q", text: question }));
  const thinking = el("div", { class: "msg a", text: "Thinking..." });
  msgs.append(thinking);
  const owner = currentId; // the analysis this question belongs to
  try {
    const answer = await requestAnswer(question);
    thinking.textContent = answer;
    chatLog.push({ q: question, a: answer });
    if (owner) { saveChat(owner, chatLog); renderHistory(); }
  } catch (err) {
    thinking.className = "msg err";
    thinking.textContent = err.message;
  } finally {
    chatBusy = false;
    $("ask-btn").disabled = false;
  }
}

/* ---------------------------------------------------------------- start */
async function main() {
  initChrome();
  magnetic([$("run")]);
  try {
    config = await loadConfig();
  } catch {
    showError("The service is not reachable right now. Please refresh the page.");
    $("run").disabled = true;
    return;
  }
  buildScale($("idle-scale"), config.regimes, { height: 84 });
  $("limit-note").textContent = `Each visitor can run ${config.limits.analyses_per_hour} analyses per hour, which keeps the service free for everyone. Your results are kept only for this visit.`;
  $("run").addEventListener("click", startAnalysis);
  $("again").addEventListener("click", () => { currentId = null; resetResult(); showView("idle"); renderHistory(); window.scrollTo({ top: 0 }); });
  $("clear-hist").addEventListener("click", () => { writeHistory([]); renderHistory(); });
  $("ask-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("ask-input");
    const q = input.value.trim();
    if (q.length < 2) return;
    input.value = "";
    ask(q);
  });
  renderHistory();
}

main();
