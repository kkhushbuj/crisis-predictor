// Top-bar extras on the home page: a History panel listing the analyses run in this tab, and a small marker while an
// analysis started in this tab is still running (with a link to its result once it has finished).
import { el, loadConfig, zoneFor, zoneColor, formatTime } from "./common.js";

const HIST_KEY = "cp_history_v1"; // same key the analysis page saves to (sessionStorage: this visit only)
const readHistory = () => { try { return JSON.parse(sessionStorage.getItem(HIST_KEY) || "[]"); } catch { return []; } };
const writeHistory = (list) => { try { sessionStorage.setItem(HIST_KEY, JSON.stringify(list)); } catch { /* storage unavailable */ } };

/* ---------------------------------------------------------------- History panel */
function initHistory() {
  const links = document.querySelector(".nav-links");
  const runBtn = links && links.querySelector(".btn-primary");
  if (!links || !runBtn) return;
  let regimes = null;
  loadConfig().then((c) => { regimes = c.regimes; if (open) render(); }).catch(() => {});

  const count = el("span", { class: "hist-count", "aria-hidden": "true" });
  const btn = el("button", { class: "hist-btn", type: "button", "aria-expanded": "false", "aria-controls": "hist-pop" }, "History", count);
  const pop = el("div", { class: "hist-pop", id: "hist-pop", role: "dialog", "aria-label": "Your analyses" });
  const wrap = el("div", { class: "hist-wrap hide-sm" }, btn, pop);
  links.insertBefore(wrap, runBtn);

  let open = false;
  const render = () => {
    const list = readHistory();
    count.textContent = list.length ? String(list.length) : "";
    count.hidden = !list.length;
    pop.textContent = "";
    pop.append(el("p", { class: "hp-title", text: "Your analyses" }), el("p", { class: "hp-note", text: "Kept for this visit only. Closing the tab clears them." }));
    if (!list.length) {
      pop.append(el("p", { class: "hp-empty", text: "Nothing yet. Run an analysis and it will be listed here." }),
        el("a", { class: "btn btn-primary hp-run", href: "/analysis", text: "Run analysis" }));
      return;
    }
    const items = el("div", { class: "hp-list" });
    list.forEach(({ id, result, chat }) => {
      const label = regimes ? zoneFor(result.composite, regimes).label : "";
      const asked = chat ? chat.length : 0;
      items.append(el("a", { class: "hp-item", href: `/analysis#open=${encodeURIComponent(id)}` },
        el("i", { style: `background:${label ? zoneColor(label) : "var(--ink-3)"}` }),
        el("b", { text: result.composite.toFixed(1) }),
        el("span", { text: `${label || "Score"}, alarm ${result.status === "ON" ? "on" : "off"}` }),
        el("small", { text: formatTime(result.created_at) + (asked ? ` · ${asked} question${asked > 1 ? "s" : ""}` : "") })));
    });
    const clear = el("button", { class: "link-btn hp-clear", type: "button", text: "Clear history" });
    clear.addEventListener("click", () => { writeHistory([]); render(); });
    pop.append(items, clear);
  };
  const setOpen = (v) => {
    open = v;
    if (v) render();
    wrap.classList.toggle("open", v);
    btn.setAttribute("aria-expanded", String(v));
  };
  btn.addEventListener("click", (e) => { e.stopPropagation(); setOpen(!open); });
  document.addEventListener("click", (e) => { if (open && !wrap.contains(e.target)) setOpen(false); });
  document.addEventListener("keydown", (e) => { if (open && e.key === "Escape") { setOpen(false); btn.focus(); } });
  window.addEventListener("scroll", () => { if (open) setOpen(false); }, { passive: true }); // scrolling away closes it
  render(); // fills the count in the button
}
initHistory();

/* ---------------------------------------------------------------- running-analysis marker */
const JOB_KEY = "cp_job_v1";
const getJob = () => { try { return sessionStorage.getItem(JOB_KEY); } catch { return null; } };
const dropJob = () => { try { sessionStorage.removeItem(JOB_KEY); } catch { /* storage unavailable */ } };

const nav = document.querySelector(".nav-links");
if (nav && getJob()) {
  const dot = document.createElement("i");
  const label = document.createElement("span");
  const pill = document.createElement("a");
  pill.href = "/analysis";
  pill.className = "run-pill";
  pill.setAttribute("role", "status");
  pill.append(dot, label);
  nav.prepend(pill);

  const show = (text, ready) => {
    pill.className = ready ? "run-pill ready" : "run-pill";
    label.textContent = text;
    pill.title = text;
    pill.setAttribute("aria-label", text);
  };
  const gone = () => { dropJob(); pill.remove(); };

  const poll = async () => {
    const id = getJob();
    if (!id) { pill.remove(); return; }
    let next = 3000;
    try {
      const res = await fetch(`/api/analyze/${id}/status`, { headers: { Accept: "application/json" } });
      if (res.status === 404) { gone(); return; }
      const s = await res.json();
      if (s.running) show(`Analysis running, ${Math.round(s.progress * 100)}%`, false);
      else if (s.has_result) { show("Analysis ready, view it", true); next = 8000; }
      else { gone(); return; }
    } catch { /* keep the last text and try again */ }
    setTimeout(poll, next);
  };
  show("Analysis running", false);
  poll();
}
