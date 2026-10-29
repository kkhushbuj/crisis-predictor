import {
  el, getJSON, loadConfig, buildScale, setupTip, revealHeading, splitWords, reduceMotion, gsap, monthYear, zoneColor, zoneFor, fontsReady, markReady,
} from "./common.js";
import { initChrome, revealOnScroll, countUp, magnetic } from "./effects.js";
import { initHow } from "./how.js";
import { initCompare } from "./compare.js";

const SVGNS = "http://www.w3.org/2000/svg";
const svg = (tag, attrs = {}) => {
  const n = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
};

/* ---------------------------------------------------------------- the four levels as a strip */
// Widths and ranges come from the server config, so the strip always agrees with the real cutoffs.
function renderLevels(config) {
  const host = document.getElementById("levels");
  if (!host) return;
  const item = (r) => el("div", { class: `level lv-${r.label.toLowerCase()}`, style: `background:${zoneColor(r.label)}` },
    el("b", { text: r.label }), el("span", { text: `${r.low} to ${r.high}` }));
  const set = () => config.regimes.map(item);
  host.append(el("div", { class: "levels-track" }, ...set(), ...set(), ...set(), ...set()));
}

/* ---------------------------------------------------------------- hero scale of 300 real dates */
function layoutDots(field, points, dots) {
  const W = field.clientWidth;
  const D = points.length > 100 ? (W < 520 ? 6 : 8) : (W < 520 ? 12 : 16), laneH = D + 3, pad = 16, gap = 30;
  dots.forEach((d) => {
    d.style.width = d.style.height = `${D}px`;
    d.style.margin = `${-D / 2}px 0 0 ${-D / 2}px`;
  });
  const groups = { stress: [], normal: [] };
  points.forEach((p, i) => groups[p.label].push({ p, i }));
  const place = (list) => {
    const lanes = [];
    const out = new Map();
    [...list].sort((a, b) => a.p.score - b.p.score).forEach(({ p, i }) => {
      const x = (p.score / 100) * W;
      let lane = lanes.findIndex((lastX) => x - lastX >= D + 3);
      if (lane === -1) { lane = lanes.length; lanes.push(x); } else lanes[lane] = x;
      out.set(i, { x, lane });
    });
    return { out, count: Math.max(lanes.length, 1) };
  };
  const s = place(groups.stress), n = place(groups.normal);
  const stressTop = pad, normalTop = pad + s.count * laneH + gap;
  field.style.height = `${normalTop + n.count * laneH + pad}px`;
  const apply = (res, top) => res.out.forEach(({ x, lane }, i) => {
    dots[i].style.left = `${x}px`;
    dots[i].style.top = `${top + lane * laneH + laneH / 2}px`;
  });
  apply(s, stressTop);
  apply(n, normalTop);
  field.querySelector(".row-stress").style.top = `${stressTop}px`;
  field.querySelector(".row-normal").style.top = `${normalTop}px`;
}

function renderHero(config, evidence) {
  const host = document.getElementById("hero-scale");
  const { field } = buildScale(host, config.regimes, { height: 200 });
  const tip = setupTip(host);
  const pts = evidence.out_of_sample;
  const mkLabel = (cls, text) => el("div", { class: `row-label ${cls}`, text });
  field.append(mkLabel("row-stress", "Stress dates"), mkLabel("row-normal", "Calm periods"));

  // the dots live in one layer, so the intro animates one element instead of three hundred
  const layer = el("div", { class: "dots-layer" });
  field.append(layer);
  const dots = pts.map((p) => {
    const flagText = p.flagged ? "Alarm would be on" : "Alarm would be off";
    const d = el("button", {
      class: `dot ${p.label === "normal" ? "normal" : ""}`, type: "button",
      "aria-label": `${p.name}: score ${p.score}. ${flagText}.`,
    });
    const show = () => tip.show(d, [p.name, `Score ${p.score}. ${flagText}.`]);
    d.addEventListener("mouseenter", show);
    d.addEventListener("focus", show);
    d.addEventListener("mouseleave", tip.hide);
    d.addEventListener("blur", tip.hide);
    layer.append(d);
    return d;
  });

  // the scale runs edge to edge: margins are measured from the real page width, which 100vw would overstate by the scrollbar
  const bleed = () => {
    host.style.marginInline = "0";
    const p = host.getBoundingClientRect();
    host.style.marginInline = `${-p.left}px ${-(document.documentElement.clientWidth - p.right)}px`;
  };
  bleed();
  new ResizeObserver(bleed).observe(document.body);

  const run = () => layoutDots(field, pts, dots);
  run();
  new ResizeObserver(() => run()).observe(field);

  // a read-out that follows the pointer along the scale: the score under it and its level
  const scrubLabel = el("div", { class: "scrub-label" });
  const scrub = el("div", { class: "scrub", "aria-hidden": "true" }, scrubLabel);
  field.append(scrub);
  let fieldLeft = 0, fieldWidth = 1;
  const measureField = () => { const r = field.getBoundingClientRect(); fieldLeft = r.left; fieldWidth = r.width || 1; };
  field.addEventListener("pointerenter", measureField);
  // at most one read-out update per frame, however many pointer events arrive
  let scrubFrame = 0, scrubX = 0;
  field.addEventListener("pointermove", (e) => {
    scrubX = e.clientX;
    if (scrubFrame) return;
    scrubFrame = requestAnimationFrame(() => {
      scrubFrame = 0;
      const pct = Math.min(100, Math.max(0, ((scrubX - fieldLeft) / fieldWidth) * 100));
      scrub.style.left = `${pct}%`;
      const shown = Math.round(pct);
      scrubLabel.textContent = `${shown}, ${zoneFor(shown, config.regimes).label}`;
      scrub.classList.add("on");
    });
  });
  field.addEventListener("pointerleave", () => scrub.classList.remove("on"));

  if (!reduceMotion && gsap) {
    gsap.fromTo(layer, { clipPath: "inset(-20px 100% -20px -20px)" }, {
      clipPath: "inset(-20px -20px -20px -20px)", duration: 1.5, ease: "power2.inOut",
      scrollTrigger: { trigger: host, start: "top 85%", once: true },
      onComplete: () => { layer.style.clipPath = "none"; },
    });
  }

  const s = evidence.summary;
  const figures = document.getElementById("figures");
  // the final number is kept in the layout (invisible) while the live one counts up on top of it, so the line breaks and widths are the
  // final ones from the first frame and nothing re-wraps or shifts while the digits grow
  const num = (n, decimals = 0) => {
    const live = el("span", { class: "cu-live", text: (0).toFixed(decimals) });
    countUp(live, n, { decimals, duration: 1.5, delay: 0.75 });
    return el("span", { class: "cu" }, el("span", { class: "cu-sizer", "aria-hidden": "true", text: n.toFixed(decimals) }), live);
  };
  const fig = (bigParts, text) => el("div", { class: "figure" }, el("b", { class: "num" }, ...bigParts), el("span", { text }));
  const small = (t) => el("small", { text: t });
  figures.append(
    fig([num(s.stress_flagged), small(` of ${s.stress_total}`)], `stress dates scored at or above the alarm line of ${evidence.threshold}`),
    fig([num(s.false_alarms), small(` of ${s.normal_total}`)], "calm dates did"),
    fig([num(s.avg_stress, 1), small(" vs "), num(s.avg_normal, 1)], "average score on stress dates against calm dates"),
    fig([num(s.auc, 2)], "AUC, how well the score ranks stress above calm (1.00 is perfect, 0.50 is a coin flip)"),
  );
}

/* ---------------------------------------------------------------- monthly charts */
function leadText(block, threshold) {
  const { first_cross: fc, lead_months: lead } = block;
  if (!fc) return `The score never reached ${threshold} in this window.`;
  const when = monthYear(fc, true);
  if (lead === 0) return `The score first reached ${threshold} in ${when}, the same month the official recession began.`;
  if (lead > 0) return `The score first reached ${threshold} in ${when}, ${lead} month${lead > 1 ? "s" : ""} before the official recession began.`;
  return `The score first reached ${threshold} in ${when}, ${-lead} month${lead < -1 ? "s" : ""} after the official recession began.`;
}

/* ["2008-02","2008-04"] -> "Feb and Apr 2008" */
function monthList(months) {
  const names = months.map((m) => new Date(`${m}-15T00:00:00Z`).toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" }));
  const years = [...new Set(months.map((m) => m.slice(0, 4)))];
  if (years.length === 1) {
    const joined = names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}` : names[0];
    return `${joined} ${years[0]}`;
  }
  return months.map((m) => monthYear(`${m}-15`)).join(", ");
}

function drawChart(block, threshold, W, H) {
  const L = 40, R = 16, T = 30, B = 44;
  const iw = W - L - R, ih = H - T - B;
  const pts = block.points, n = pts.length;
  const lo = 40, hi = 80;
  const x = (i) => L + (i / (n - 1)) * iw;
  const y = (v) => T + (1 - (v - lo) / (hi - lo)) * ih;
  const step = iw / (n - 1);
  const root = svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${block.title}: monthly Crisis Score against the alarm line of ${threshold}` });

  // recession bands
  let i = 0;
  while (i < n) {
    if (pts[i].recession) {
      let j = i;
      while (j + 1 < n && pts[j + 1].recession) j++;
      root.append(svg("rect", { x: x(i) - step / 2, y: T, width: (j - i + 1) * step, height: ih, fill: "rgba(255,255,255,0.12)" }));
      i = j + 1;
    } else i++;
  }
  // y labels
  [40, 60, 80].forEach((v) => {
    const t = svg("text", { x: L - 10, y: y(v) + 4, "text-anchor": "end" });
    t.textContent = v;
    root.append(t);
  });
  // alarm line
  root.append(svg("rect", { x: L, y: y(threshold) - 1.5, width: iw, height: 3, fill: "var(--stress)" }));
  const al = svg("text", { x: L + 8, y: y(threshold) - 10, fill: "var(--stress)" });
  al.style.fill = "var(--stress)";
  al.textContent = `Alarm ${threshold}`;
  root.append(al);
  // x labels
  [0, Math.floor((n - 1) / 2), n - 1].forEach((k, idx) => {
    const t = svg("text", { x: x(k), y: H - 12, "text-anchor": idx === 0 ? "start" : idx === 2 ? "end" : "middle" });
    t.textContent = monthYear(pts[k].date);
    root.append(t);
  });
  // line
  const d = pts.map((p, k) => `${k ? "L" : "M"}${x(k).toFixed(1)} ${y(p.score).toFixed(1)}`).join(" ");
  const path = svg("path", { d, fill: "none", stroke: "#8fa0ff", "stroke-width": 3.5, "stroke-linejoin": "round", "stroke-linecap": "round" });
  root.append(path);
  const circles = pts.map((p, k) => {
    const c = svg("circle", { cx: x(k), cy: y(p.score), r: 5, fill: p.score >= threshold ? "#ffffff" : "#8fa0ff" });
    const tt = svg("title");
    tt.textContent = `${monthYear(p.date)}: ${p.score}`;
    c.append(tt);
    root.append(c);
    return c;
  });
  // peak label
  const pk = pts.findIndex((p) => p.date === block.peak.date);
  const pl = svg("text", { x: Math.min(Math.max(x(pk), L + 60), W - R - 60), y: y(block.peak.score) - 14, "text-anchor": "middle" });
  pl.style.fill = "#ffffff";
  pl.style.fontWeight = "600";
  pl.textContent = `Peak ${block.peak.score}`;
  root.append(pl);

  return { root, path, circles, peakLabel: pl };
}

/* Draws the chart at its real pixel width (so text stays readable) and redraws on resize. The line draws as you scroll. */
function mountChart(holder, block, thr) {
  let trigger = null, lastW = 0, progress = reduceMotion ? 1 : 0;
  const build = () => {
    const w = Math.round(holder.clientWidth);
    if (!w || Math.abs(w - lastW) < 6) return;
    lastW = w;
    if (trigger) trigger.kill();
    holder.textContent = "";
    const { root, path, circles, peakLabel } = drawChart(block, thr, w, w < 520 ? 300 : 340);
    holder.append(root);
    if (reduceMotion || !gsap || !window.ScrollTrigger) return;
    const len = path.getTotalLength();
    path.style.strokeDasharray = len;
    const apply = (p) => {
      path.style.strokeDashoffset = len * (1 - p);
      circles.forEach((c, k) => (c.style.opacity = k / (circles.length - 1) <= p + 0.001 ? 1 : 0));
      peakLabel.style.opacity = p > 0.96 ? 1 : 0;
    };
    trigger = window.ScrollTrigger.create({
      trigger: root, start: "top 82%", end: "bottom 48%",
      onUpdate: (self) => { progress = self.progress; apply(progress); },
    });
    progress = trigger.progress;
    apply(progress);
  };
  build();
  new ResizeObserver(build).observe(holder);
}

function renderCharts(config, evidence) {
  const host = document.getElementById("charts");
  const thr = evidence.threshold;
  const blocks = [evidence.monthly.gfc, evidence.monthly.covid];
  blocks.forEach((b) => {
    const dips = b.back_under_during_recession || [];
    const dipText = dips.length
      ? ` It fell back under the line in ${monthList(dips)} while the recession was already under way.`
      : "";
    const cap = el("figcaption", { class: "cap" }, el("b", { text: leadText(b, thr) }), `${dipText} Highest score: ${b.peak.score} in ${monthYear(b.peak.date)}.`);
    const holder = el("div", { class: "chart-holder" });
    host.append(el("figure", { class: "chart" }, el("h3", { text: b.title }), holder, cap));
    mountChart(holder, b, thr);
  });

  const leads = blocks.map((b) => b.lead_months);
  const reading = document.getElementById("reading");
  if (leads.every((l) => l === 0)) {
    reading.textContent = "Honest reading: in both episodes the score reached the alarm line in the same month the recession began, not before. It confirms stress as it arrives. In these tests it did not give months of advance warning.";
  } else if (leads.every((l) => l > 0)) {
    reading.textContent = "Reading: in both episodes the score reached the alarm line before the recession was officially dated, though the margin was small and two episodes are not proof.";
  } else {
    reading.textContent = "Reading: the score's timing against official recession dates was mixed across the two episodes, so it should not be treated as a reliable early warning on this evidence.";
  }
}

/* ---------------------------------------------------------------- signals + limits */
function renderSignals(config) {
  const host = document.getElementById("signals");
  config.categories.forEach((c) => {
    host.append(el("div", {},
      el("h3", { text: c.label }),
      el("ul", {}, c.factors.map((f) => el("li", { text: f.label })))));
  });
}

function renderLimits(config, evidence) {
  const s = evidence.summary;
  const missed = s.stress_total - s.stress_flagged;
  const cuts = config.regimes.map((r) => r.low).filter((v) => v > 0).join(", ");
  const items = [
    ["It detects stress. It has not been shown to predict it.", "In the monthly tests of 2008 and 2020 the score reached the alarm line in the same month the official recession began, not before. So it confirms stress as it arrives and has not shown months of advance warning."],
    ["It misses many stress days.", `The alarm was on for ${s.stress_flagged} of ${s.stress_total} stress dates, so it missed ${missed}. ${s.missed_near_line} of the misses scored within 5 points of the alarm line. A lower alarm line catches more, but gives more false alarms.`],
    ["The news in the tests was written from history.", "A live search cannot look back, so the news summaries for past dates were written from the historical record. Treat the news part of these results as less independent than the market data."],
    [`${s.total} dates is still a modest sample.`, `The level boundaries (${cuts}) are working values, not proven constants. The dates were drawn from known stress and calm periods, so the results show how well it separates them, not how it would score every ordinary day.`],
    ["It is not advice.", "It is an academic tool built to explain risk. It does not tell anyone what to buy or sell."],
  ];
  const host = document.getElementById("limits-list");
  items.forEach(([b, t]) => host.append(el("p", {}, el("b", { text: b + " " }), t)));
}

/* ---------------------------------------------------------------- start */
async function main() {
  initChrome();
  magnetic(document.querySelectorAll(".hero .btn-primary, .cta .btn-primary, .nav .btn-primary"));
  // start loading the data now, in parallel with the fonts, instead of after the page has been drawn
  const data = Promise.all([loadConfig(), getJSON("/assets/data/evidence.json")]);
  data.catch(() => {}); // handled below
  await fontsReady();
  const hero = document.getElementById("hero-title");
  const heroWords = splitWords(hero);
  const heroIntro = ["#hero-lead", "#hero-actions", ".hero-proof"]; // they rise in one after another, once the page is showing
  if (!reduceMotion && gsap) { gsap.set(heroWords, { yPercent: 115 }); gsap.set(heroIntro, { opacity: 0, y: 18 }); } // hidden before the page fades in
  document.querySelectorAll("[data-reveal]").forEach((h) => revealHeading(h));

  // the page stays hidden until the data is in and drawn (at most 1.5 s more), so it opens complete instead of filling in piece by piece
  const loaded = await Promise.race([data.then(() => true, () => false), new Promise((resolve) => setTimeout(() => resolve(false), 1500))]);
  try {
    if (!loaded) throw new Error("slow");
    const [config, evidence] = await data;
    renderLevels(config);
    renderHero(config, evidence);
    renderCharts(config, evidence);
    renderSignals(config);
    renderLimits(config, evidence);
    initHow(config, evidence);
    initCompare(config, evidence);
    revealOnScroll(".signals > div");
    revealOnScroll(".limits p");
    if (window.ScrollTrigger) window.ScrollTrigger.refresh();
  } catch (err) {
    console.error(err);
    document.getElementById("proof").append(el("p", { class: "error-box", text: "The evidence could not be loaded. Please refresh the page." }));
  }

  markReady();
  revealHeading(hero, { onScroll: false });
  if (!reduceMotion && gsap) {
    gsap.to(heroIntro, { opacity: 1, y: 0, duration: 0.8, ease: "power3.out", delay: 0.3, stagger: 0.14 });
    setTimeout(() => gsap.set(heroIntro, { opacity: 1, y: 0 }), 4500); // safety: always visible
  }
}

main();
