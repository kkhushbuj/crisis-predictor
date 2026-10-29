import { el, buildScale, zoneFor, zoneColor } from "./common.js";
import { countUp } from "./effects.js";

/* "How it works": the left stage changes as each step scrolls to the middle of the screen, and a guide line fills
   as you move down the steps. Every number shown comes from the real model or the real backtest. */

const VIX_RULES = [
  ["VIX above 40, panic", 50, "-10", "neg"],
  ["30 to 40, acute stress", 35, "-7", "neg"],
  ["20 to 30, elevated concern", 15, "-3", "neg"],
  ["15 to 20, normal", 0, "0", "zero"],
  ["Below 15, calm", 25, "+5", "pos"],
];

function viewSources() {
  const row = (n, name, text) => el("div", { class: "src-row" }, el("b", { text: String(n) }), el("div", {}, el("strong", { text: name }), el("span", { text })));
  return el("div", { class: "stage-view" },
    el("p", { class: "stage-tag", text: "Where the fourteen signals come from" }),
    row(6, "FRED", "Yield curve, credit spread, jobless claims, CPI, repo rates and the money supply"),
    row(6, "Yahoo Finance", "VIX, S&P 500 drawdown, gold, the US dollar, bank stocks and oil"),
    row(2, "Live news search", "Tariffs and sanctions, and geopolitical conflict"));
}

function viewRule() {
  const rows = VIX_RULES.map(([label, w, score, cls]) => el("div", { class: "mini-row", role: "row" },
    el("span", { text: label }),
    el("div", { class: "diverge", "aria-hidden": "true" }, w ? el("i", { class: cls === "pos" ? "pos" : "neg", style: `width:${w}%` }) : null),
    el("b", { class: cls, text: score })));
  const view = el("div", { class: "stage-view" },
    el("p", { class: "stage-tag", text: "The rule for one signal, the VIX" }),
    el("span", { class: "rule-chip", text: "Example: the VIX is at 18.6" }),
    el("div", { class: "mini", role: "table", "aria-label": "Scoring rule for the VIX" }, rows),
    el("p", { class: "stage-note", text: "It falls in the 15 to 20 band, so this signal scores 0." }));
  view._enter = () => setTimeout(() => rows[3].classList.add("hit"), 450);
  view._leave = () => rows[3].classList.remove("hit");
  return view;
}

function viewWeights(config) {
  const bar = el("div", { class: "weights", role: "img", "aria-label": "How the four categories are weighted" });
  config.categories.forEach((c) => {
    const short = c.label.split(/[ /]/)[0];
    bar.append(el("div", { style: `--w:${c.weight}%`, title: c.label }, `${short} ${c.weight}%`));
  });
  return el("div", { class: "stage-view" },
    el("p", { class: "stage-tag", text: "How much each category counts" }),
    bar,
    el("p", { class: "stage-note", text: "Fixed in code. The AI only scores signals, it never sets these." }));
}

function viewResult(config, panic) {
  const zone = zoneFor(panic.score, config.regimes);
  const host = el("div");
  const { field } = buildScale(host, config.regimes, { height: 84 });
  const needle = el("div", { class: "needle", style: "top:-10px;height:104px;left:0%" });
  host.append(needle);
  const num = el("span", { text: "0.0" });
  const view = el("div", { class: "stage-view" },
    el("p", { class: "stage-tag", text: `Example: ${panic.name}` }),
    el("div", { class: "stage-score" }, num, el("small", { text: `/ 100, ${zone.label}, alarm ${panic.flagged ? "on" : "off"}` })),
    host);
  void field;
  view._enter = () => {
    setTimeout(() => { needle.style.left = `${panic.score}%`; }, 150);
    countUp(num, panic.score, { decimals: 1, duration: 1.6, delay: 0.15 });
  };
  view._leave = () => { needle.style.left = "0%"; num.textContent = "0.0"; };
  view._color = zoneColor(zone.label);
  return view;
}

export function initHow(config, evidence) {
  const stage = document.getElementById("stage");
  const steps = [...document.querySelectorAll("#steps > li")];
  const beam = document.getElementById("beam-fill");
  const wrap = document.getElementById("steps-wrap");
  if (!stage || !steps.length) return;

  const wide = window.matchMedia("(min-width: 900px)");
  let views = [];
  let active = -1;

  const setActive = (idx) => {
    if (idx === active) return;
    const prev = active;
    active = idx;
    steps.forEach((li, i) => {
      li.classList.toggle("active", i === idx);
      li.classList.toggle("passed", i < idx);
    });
    views.forEach((v, i) => {
      const on = wide.matches ? i === idx : i <= idx;
      const was = v.classList.contains("on");
      v.classList.toggle("on", on);
      if (on && !was && v._enter) v._enter();
      if (!on && was && v._leave) v._leave();
    });
    void prev;
  };

  const mount = () => {
    stage.textContent = "";
    steps.forEach((li) => li.querySelectorAll(".stage-view").forEach((v) => v.remove()));
    views = [viewSources(), viewRule(), viewWeights(config), viewResult(config, evidence.compare.panic)];
    stage.hidden = !wide.matches;
    views.forEach((v, i) => (wide.matches ? stage.append(v) : steps[i].append(v)));
    active = -1;
    setActive(Math.max(0, steps.findIndex((li) => li.getBoundingClientRect().top > window.innerHeight * 0.4) - 1));
  };

  const pick = () => {
    const mid = window.innerHeight * 0.5;
    let idx = 0;
    steps.forEach((li, i) => { if (li.getBoundingClientRect().top < mid + 40) idx = i; });
    setActive(idx);
    if (beam && wrap) {
      const r = wrap.getBoundingClientRect();
      const pct = Math.min(1, Math.max(0, (mid - r.top) / r.height));
      beam.style.height = `${pct * 100}%`;
    }
  };

  // at most one update per frame, however many scroll events arrive
  let queued = false;
  const pickSoon = () => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; pick(); }); } };

  mount();
  pick();
  window.addEventListener("scroll", pickSoon, { passive: true });
  window.addEventListener("resize", pickSoon);
  wide.addEventListener("change", () => { mount(); pick(); });
}
