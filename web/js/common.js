// Shared helpers for the landing and analysis pages. All dynamic text is set with textContent (never innerHTML).

export const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const gsap = window.gsap;
if (gsap && window.ScrollTrigger) gsap.registerPlugin(window.ScrollTrigger);

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return node;
}

export async function getJSON(url) {
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${url} returned ${res.status}`);
  return res.json();
}

export const loadConfig = () => getJSON("/api/config");

export function zoneFor(score, regimes) {
  return regimes.find((r) => score >= r.low && score < r.high) || regimes[regimes.length - 1];
}

const ZONE_COLORS = { Calm: "var(--calm)", Elevated: "var(--elevated)", Stress: "var(--stress)", Crisis: "var(--crisis)" };
export const zoneColor = (label) => ZONE_COLORS[label] || "var(--ink-3)";

export function monthYear(iso, long = false) {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("en-GB", { month: long ? "long" : "short", year: "numeric", timeZone: "UTC" });
}

export function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/* Splits a heading into words, each wrapped so it can rise out of a mask. */
export function splitWords(node) {
  if (node.dataset.split) return [...node.querySelectorAll(".wi")];
  const text = node.textContent.trim();
  node.setAttribute("aria-label", text);
  node.textContent = "";
  const spans = [];
  text.split(/\s+/).forEach((word, i, all) => {
    const inner = el("span", { class: "wi", "aria-hidden": "true", text: word });
    node.append(el("span", { class: "w" }, inner));
    if (i < all.length - 1) node.append(" ");
    spans.push(inner);
  });
  node.dataset.split = "1";
  return spans;
}

export function revealHeading(node, { onScroll = true, delay = 0 } = {}) {
  const words = splitWords(node);
  if (reduceMotion || !gsap) return;
  gsap.set(words, { yPercent: 115 });
  const play = () => {
    gsap.to(words, { yPercent: 0, duration: 1.05, ease: "power4.out", stagger: 0.07, delay });
    setTimeout(() => gsap.set(words, { yPercent: 0 }), 4500); // safety: never leave a heading hidden if an animation stalls
  };
  if (onScroll && window.ScrollTrigger) {
    window.ScrollTrigger.create({ trigger: node, start: "top 88%", once: true, onEnter: play });
  } else play();
}

/* The 0-100 risk scale. Zone widths come from the server config, so a changed cutoff updates every page. */
export function buildScale(container, regimes, { height = 84, names = true } = {}) {
  container.textContent = "";
  container.classList.add("scale");
  const field = el("div", { class: "scale-field", style: `height:${height}px` });
  regimes.forEach((r) => {
    const z = el("div", { class: "zone", style: `width:${r.high - r.low}%` });
    z.append(el("div", { class: "zone-fill", style: `background:${zoneColor(r.label)}` }));
    field.append(z);
  });
  container.append(field);
  if (names) {
    const row = el("div", { class: "zone-names" });
    regimes.forEach((r) => {
      row.append(el("div", { class: "zone-name", style: `width:${r.high - r.low}%` }, r.label, el("span", { text: `${r.low}` })));
    });
    container.append(row);
  }
  return { field };
}

export function setupTip(container) {
  const tip = el("div", { class: "tip", role: "status" });
  container.append(tip);
  return {
    show(target, lines) {
      tip.textContent = "";
      tip.append(el("b", { text: lines[0] }), lines[1] || "");
      const c = container.getBoundingClientRect();
      const t = target.getBoundingClientRect();
      const x = Math.min(Math.max(t.left - c.left + t.width / 2, 120), c.width - 120);
      tip.style.left = `${x}px`;
      tip.style.top = `${t.top - c.top}px`;
      tip.classList.add("show");
    },
    hide() { tip.classList.remove("show"); },
  };
}

export { gsap };
