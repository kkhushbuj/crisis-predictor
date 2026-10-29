import { el, loadConfig, buildScale, zoneFor, zoneColor, reduceMotion, gsap, formatTime, fontsReady, markReady } from "./common.js";
import { initChrome, magnetic, glideToTop } from "./effects.js";

const $ = (id) => document.getElementById(id);
const HIST_KEY = "cp_history_v1";
// The id of the analysis running for this tab. It lets this page reconnect to it after a visit to another page, and lets
// the other pages show that it is still running (see status.js).
const JOB_KEY = "cp_job_v1";
const readJob = () => { try { return sessionStorage.getItem(JOB_KEY); } catch { return null; } };
const writeJob = (id) => { try { if (id) sessionStorage.setItem(JOB_KEY, id); else sessionStorage.removeItem(JOB_KEY); } catch { /* storage unavailable */ } };
// darker shades of the four level colours, so the big score number stays readable on the light page
const LEVEL_INK = { Calm: "#217a4e", Elevated: "#9c7300", Stress: "#c2570a", Crisis: "#d3213f" };

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
      el("i", { class: "lv", style: `background:${zoneColor(zone.label)}` }),
      el("b", { text: result.composite.toFixed(1) }),
      el("span", { text: `${zone.label}, alarm ${result.status === "ON" ? "on" : "off"}` }),
      el("small", { text: formatTime(result.created_at) + (asked ? ` · ${asked} question${asked > 1 ? "s" : ""}` : "") }));
    b.addEventListener("click", () => {
      if (running) return;
      currentId = id;
      fadeOutCurrent().then(() => showResult(result, { animate: false, fromHistory: true, chat: chat || [] }));
    });
    host.append(b);
  });
}

/* ---------------------------------------------------------------- views */
const VIEWS = ["view-idle", "view-run", "view-answer"];
/* The page that is showing fades out first (about a fifth of a second), so changing view never snaps. showView then swaps and the new view fades in. */
function fadeOutCurrent() {
  const cur = VIEWS.map($).find((v) => !v.hidden);
  if (!cur || reduceMotion) return Promise.resolve();
  cur.classList.add("fading-out");
  return new Promise((resolve) => setTimeout(resolve, 220));
}
function showView(name) {
  VIEWS.forEach((id) => $(id).classList.remove("fading-out"));
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
  closeReveal($("signals-panel"));
  $("pair").hidden = true;
  $("groups").textContent = "";
  $("flat").textContent = "";
  $("sig-sort").hidden = true;
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
  const text = STATUS_TEXT[Math.min(doneCount, STATUS_TEXT.length - 1)];
  if (line && line.textContent !== text) {
    if (reduceMotion || !line.textContent) line.textContent = text;
    else { // the old line fades out, the new one fades in
      line.classList.add("swap");
      setTimeout(() => { line.textContent = text; line.classList.remove("swap"); }, 250);
    }
  }
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
      el("div", { class: "f-why-wrap" }, el("div", {}, el("div", { class: "f-why", text: f.reasoning || "No reason recorded." })))),
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

/* Shows a hidden block. When it is new and animate is on, it grows open (see .reveal-h in bold.css) instead of appearing at full height. */
function openReveal(node, animate) {
  const wasHidden = node.hidden;
  node.hidden = false;
  if (!wasHidden && node.classList.contains("open")) return;
  if (animate && !reduceMotion) {
    node.classList.add("animating");
    requestAnimationFrame(() => requestAnimationFrame(() => node.classList.add("open"))); // two frames, so the closed state is drawn first
    setTimeout(() => node.classList.add("settled"), 1200); // once fully open it stops clipping its content
  } else {
    node.classList.remove("animating");
    node.classList.add("open", "settled");
  }
}
function closeReveal(node) {
  node.hidden = true;
  node.classList.remove("open", "animating", "settled");
}

function groupBlock(catKey, animate) {
  let g = document.getElementById(`group-${catKey}`);
  if (g) return g.querySelector(".rows");
  const cat = config.categories.find((c) => c.key === catKey);
  g = el("div", { class: "group reveal-h", id: `group-${catKey}` }, el("div", { class: "reveal-in" },
    el("h3", {}, cat.label, el("span", { text: `${cat.weight}% of the score` })),
    el("div", { class: "rows" })));
  $("groups").append(g);
  openReveal(g, animate);
  return g.querySelector(".rows");
}

function addFactors(catKey, factors, animate) {
  openReveal($("signals-panel"), animate);
  const rows = groupBlock(catKey, animate);
  const cat = config.categories.find((c) => c.key === catKey);
  cat.factors.filter((f) => factors[f.key]).forEach((f) => rows.append(factorRow(factors[f.key])));
}

/* ---------------------------------------------------------------- live counter, order switch, sticky score */
function updateScored() {
  const done = $("groups").querySelectorAll(".factor").length;
  const total = config.categories.reduce((n, c) => n + c.factors.length, 0);
  $("scored").textContent = `${done} of ${total} signals scored`;
}

function buildFlat() {
  const flat = $("flat");
  flat.textContent = "";
  const rows = [];
  current.categories.forEach((c) => Object.values(c.factors).forEach((f) => rows.push({ f, cat: c.label })));
  rows.sort((a, b) => (a.f.score ?? 0) - (b.f.score ?? 0));
  rows.forEach(({ f, cat }) => {
    const row = factorRow(f);
    row.querySelector(".f-name").append(el("span", { class: "f-cat", text: cat }));
    flat.append(row);
  });
}

/* Switching between "By category" and "Most worrying first": the list on screen fades out, the other one fades in, and the height
   glides from the old size to the new one, so nothing snaps and the page below does not jump. */
let sortToken = 0;
const clearSwapStyles = (n) => { n.classList.remove("fade-out"); ["height", "overflow", "opacity", "transition"].forEach((p) => n.style.removeProperty(p)); };
function setSort(mode, animate = false) {
  document.querySelectorAll("#sig-sort button").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
  const worst = mode === "worst" && current;
  const showing = worst ? $("flat") : $("groups");
  const hiding = worst ? $("groups") : $("flat");
  const token = ++sortToken; // a quick second click cancels the first change
  clearSwapStyles(showing);
  clearSwapStyles(hiding);
  if (!animate || reduceMotion || hiding.hidden || !showing.hidden) {
    if (worst) buildFlat();
    hiding.hidden = true;
    showing.hidden = false;
    return;
  }
  const fromH = hiding.offsetHeight;
  hiding.classList.add("fade-out");
  setTimeout(() => {
    if (token !== sortToken) return;
    clearSwapStyles(hiding);
    hiding.hidden = true;
    if (worst) buildFlat();
    showing.hidden = false;
    const toH = showing.offsetHeight;
    showing.style.overflow = "hidden";
    showing.style.height = `${fromH}px`;
    showing.style.opacity = "0";
    showing.getBoundingClientRect(); // draw the starting size before changing it
    showing.style.transition = "height 0.5s cubic-bezier(0.2, 0.7, 0.2, 1), opacity 0.4s ease";
    showing.style.height = `${toH}px`;
    showing.style.opacity = "1";
    setTimeout(() => { if (token === sortToken) clearSwapStyles(showing); }, 560);
  }, 190);
}

function updateMini(result, zone) {
  const mini = $("mini-bar");
  mini.textContent = "";
  mini.style.setProperty("--c", zoneColor(zone.label));
  mini.append(el("i"), el("b", { text: result.composite.toFixed(1) }), el("span", { text: `${zone.label}, alarm ${result.status === "ON" ? "on" : "off"}` }));
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
  sn.style.color = LEVEL_INK[zone.label] || "";
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
    const fill = el("i", { style: `width:${animate && !reduceMotion ? 0 : c.crisis_pct}%;background:${zoneColor(zoneFor(c.crisis_pct, config.regimes).label)}` });
    fills.push([fill, c.crisis_pct]);
    rows.append(el("div", { class: "cat-row" },
      el("div", { class: "name" }, c.label, el("span", { text: `weight ${c.weight}%` })),
      el("div", { class: "track", "aria-label": `${c.label} worry level ${c.crisis_pct} out of 100` }, fill),
      el("div", { class: "pts" }, c.points.toFixed(1), el("small", { text: " pts" }))));
  });
  $("drivers").hidden = false;

  // signals (rows already exist after a live run; rebuild when loading from history)
  openReveal($("signals-panel"), false);
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

  $("sig-sort").hidden = false;
  setSort("cat");
  updateMini(result, zone);
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
async function startAnalysis(resumeId = null) {
  if (running) return;
  running = true;
  $("run").disabled = true;
  showError("");
  resetResult();
  current = null;
  currentId = null;
  const chips = buildStages();
  setStages(chips, 0);
  updateScored();
  $("bar").style.width = "4%";
  // the request starts straight away; the screen change plays at the same time and never delays the analysis
  const pending = resumeId
    ? fetch(`/api/analyze/${resumeId}/stream`, { headers: { Accept: "text/event-stream" } })
    : fetch("/api/analyze", { method: "POST", headers: { Accept: "text/event-stream" } });
  pending.catch(() => {}); // a failure is reported below, where the response is read
  await glideToTop(true);
  await fadeOutCurrent();
  showView("run");
  window.scrollTo({ top: 0, behavior: "auto" });

  const nodeIndex = { credit_systemic: 1, liquidity_shock: 2, macro: 3, geopolitical: 4 };
  let finished = false;
  try {
    // a new run starts a job; a resumed one reconnects to the job and replays what it has done so far
    const res = await pending;
    if (!res.ok) {
      if (resumeId) writeJob(null);
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
        if (ev.type === "job") {
          writeJob(ev.id);
        } else if (ev.type === "node") {
          $("bar").style.width = `${Math.max(4, ev.progress * 100)}%`;
          if (ev.category) {
            addFactors(ev.category, ev.factors, true);
            updateScored();
            setStages(chips, nodeIndex[ev.category]);
          } else {
            setStages(chips, STAGES.length);
          }
        } else if (ev.type === "result") {
          finished = true;
          writeJob(null);
          // the reader is brought up to the top first (scrolling paused for a moment), so the score appears in front of them instead of the page jumping under them
          await glideToTop(true);
          await fadeOutCurrent();
          currentId = saveHistory(ev.result);
          showResult(ev.result, { animate: true });
        } else if (ev.type === "error") {
          writeJob(null);
          throw new Error(ev.message);
        }
      }
    }
    if (!finished) { writeJob(null); throw new Error("The analysis ended early. Please try again."); }
  } catch (err) {
    const dropped = err instanceof TypeError; // fetch reports a dropped connection as a TypeError
    showError(dropped ? "The connection was interrupted. Your analysis may still be running: reload this page to pick it up again." : err.message || "Something went wrong. Please try again.");
    $("groups").textContent = "";
    closeReveal($("signals-panel"));
    await fadeOutCurrent();
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

/* Reads the answer as the server writes it. onText gets each new piece; the full answer is returned at the end.
   If nothing has arrived yet, a failed call is retried once. */
async function requestAnswer(question, onText) {
  const history = chatLog.slice(-4).flatMap((m) => [{ role: "user", content: m.q }, { role: "assistant", content: m.a }]);
  let lastError = new Error("Could not answer right now. Please try again.");
  for (let attempt = 0; attempt < 2; attempt++) {
    let full = "";
    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, context: chatContext(), history }),
      });
      if (!res.ok || !res.body) {
        const data = await res.json().catch(() => ({}));
        lastError = new Error(data.error || (data.detail ? "Please ask a longer question." : "Could not answer right now. Please try again."));
        if (res.status === 429 || res.status === 422) break; // retrying will not help
        continue;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        const piece = decoder.decode(value, { stream: true });
        full += piece;
        onText(piece);
      }
      if (full.trim()) return full.trim();
      lastError = new Error("Could not answer right now. Please try again.");
    } catch (err) {
      if (full.trim()) return full.trim(); // the connection dropped after most of the answer arrived: keep what we have
      lastError = new Error("The connection was interrupted. Please try again.");
    }
  }
  throw lastError;
}

/* Types text into a bubble at an even pace, however the pieces arrive: a larger backlog is shown faster, so it never lags far behind. */
function typewriter(node, onTick) {
  let queue = "", shown = "", finished = false, resolveDone, last = performance.now(), owed = 0;
  const done = new Promise((r) => { resolveDone = r; });
  const tick = (now) => {
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (queue) {
      // a steady reading pace (about 55 characters a second), a little quicker when a long backlog builds up, never faster than 110
      owed += Math.min(55 + queue.length * 0.1, 110) * dt;
      const n = (reduceMotion || document.hidden) ? queue.length : Math.floor(owed);
      if (n > 0) {
        owed -= n;
        shown += queue.slice(0, n);
        queue = queue.slice(n);
        node.textContent = shown;
        if (onTick) onTick();
      }
    }
    if (queue || !finished) requestAnimationFrame(tick);
    else resolveDone();
  };
  requestAnimationFrame(tick);
  return { push(t) { queue += t; }, finish() { finished = true; }, done };
}

async function ask(question) {
  if (!current || chatBusy) return;
  chatBusy = true;
  $("ask-btn").disabled = true;
  $("suggest").textContent = "";
  const msgs = $("msgs");
  msgs.append(el("div", { class: "msg q", text: question }));
  const thinking = el("div", { class: "msg a thinking", "aria-live": "polite" },
    el("span", { class: "dots", "aria-hidden": "true" }, el("i"), el("i"), el("i")), el("span", { class: "think-label", text: "Reading the analysis" }));
  msgs.append(thinking);
  const owner = currentId; // the analysis this question belongs to
  let typer = null;

  // keep the newest text and the question box on screen while the answer grows, until the reader scrolls up on their own
  let following = true;
  const stopFollowing = (e) => { if (e.type !== "wheel" || e.deltaY < 0) following = false; };
  const stopKeys = (e) => { if (["ArrowUp", "PageUp", "Home"].includes(e.key)) following = false; };
  window.addEventListener("wheel", stopFollowing, { passive: true });
  window.addEventListener("touchmove", stopFollowing, { passive: true });
  window.addEventListener("keydown", stopKeys);
  const follow = () => {
    if (!following) return;
    const over = $("ask-btn").getBoundingClientRect().bottom - (window.innerHeight - 28);
    if (over > 0) window.scrollBy({ top: over, behavior: "instant" });
  };
  follow();
  try {
    const answer = await requestAnswer(question, (piece) => {
      if (!typer) {
        thinking.textContent = ""; // the first words have arrived: swap the dots for the answer
        thinking.classList.remove("thinking");
        thinking.classList.add("streaming");
        typer = typewriter(thinking, follow);
      }
      typer.push(piece);
    });
    typer.finish();
    await typer.done;
    thinking.classList.remove("streaming");
    thinking.textContent = answer;
    follow();
    chatLog.push({ q: question, a: answer });
    if (owner) { saveChat(owner, chatLog); renderHistory(); }
  } catch (err) {
    if (typer) typer.finish();
    thinking.className = "msg err";
    thinking.textContent = err.message;
  } finally {
    window.removeEventListener("wheel", stopFollowing);
    window.removeEventListener("touchmove", stopFollowing);
    window.removeEventListener("keydown", stopKeys);
    chatBusy = false;
    $("ask-btn").disabled = false;
  }
}

/* ---------------------------------------------------------------- start */
async function main() {
  initChrome();
  magnetic([$("run")]);
  const cfg = loadConfig();
  cfg.catch(() => {}); // handled below
  await fontsReady();
  markReady();
  try {
    config = await cfg;
  } catch {
    showError("The service is not reachable right now. Please refresh the page.");
    $("run").disabled = true;
    return;
  }
  buildScale($("idle-scale"), config.regimes, { height: 84 });
  const nFactors = config.categories.reduce((n, c) => n + c.factors.length, 0);
  [[nFactors, "signals scored"], [config.categories.length, "categories"], ["45s", "about, start to finish"]].forEach(([v, t]) => {
    $("facts").append(el("div", { class: "fact" }, el("b", { text: String(v) }), el("span", { text: t })));
  });
  document.querySelectorAll("#sig-sort button").forEach((b) => b.addEventListener("click", () => setSort(b.dataset.mode, true)));
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => $("mini-bar").classList.toggle("show", !e.isIntersecting && !$("view-answer").hidden), { rootMargin: "-70px 0px 0px 0px" }).observe($("score-num"));
  }
  $("limit-note").textContent = `Each visitor can run ${config.limits.analyses_per_hour} analyses per hour, which keeps the service free for everyone. Your results are kept only for this visit.`;
  $("run").addEventListener("click", () => startAnalysis());
  $("again").addEventListener("click", () => { fadeOutCurrent().then(() => { currentId = null; resetResult(); showView("idle"); renderHistory(); window.scrollTo({ top: 0 }); }); });
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
  const saved = readJob();
  if (saved) startAnalysis(saved); // an analysis was running when this tab last left the page
}

main();
