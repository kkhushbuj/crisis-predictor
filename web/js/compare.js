import { el, buildScale, zoneFor, zoneColor, reduceMotion, gsap } from "./common.js";

/* Drag-to-compare: the calmest and the most stressed day of the 300-date test, side by side on the same scale. */

function panel(kind, p, config) {
  const zone = zoneFor(p.score, config.regimes);
  const scaleHost = el("div", { class: "cmp-scale" });
  buildScale(scaleHost, config.regimes, { height: 26, names: false });
  scaleHost.append(el("div", { class: "needle", style: `left:${p.score}%` }));
  const fact = (value, label) => el("div", {}, el("b", { text: value }), label);
  const drawdown = `${p.drawdown.toFixed(1)}%`;
  return el("div", { class: `cmp-panel ${kind}` },
    el("div", { class: "cmp-inner" },
      el("div", { class: "cmp-when", text: p.name }),
      el("div", { class: "cmp-big", text: p.score.toFixed(1) }),
      el("div", { class: "cmp-chips" },
        el("span", { class: "chip level", style: `background:${zoneColor(zone.label)};${zone.label === "Elevated" ? "color:var(--ink)" : ""}`, text: zone.label }),
        el("span", { class: `chip ${p.flagged ? "on" : ""}` }, el("i"), p.flagged ? "Alarm on" : "Alarm off")),
      scaleHost,
      el("div", { class: "cmp-facts" }, fact(p.vix.toFixed(1), "VIX, the fear gauge"), fact(drawdown, "S&P 500 from its high"))));
}

export function initCompare(config, evidence) {
  const box = document.getElementById("compare-box");
  if (!box || !evidence.compare) return;
  const { calm, panic } = evidence.compare;

  const handle = el("div", {
    class: "cmp-handle", role: "slider", tabindex: "0", "aria-label": "Move between a calm day and a day of market panic",
    "aria-valuemin": "8", "aria-valuemax": "92", "aria-valuenow": "50",
  });
  box.append(panel("calm", calm, config), panel("panic", panic, config), handle);
  box.after(el("p", { class: "cmp-hint", text: "Drag the handle or press the left and right arrow keys. Both scores come from the same model and the same weights." }));

  let cut = 50;
  const setCut = (v) => {
    cut = Math.min(92, Math.max(8, v));
    box.style.setProperty("--cut", `${cut}%`);
    handle.setAttribute("aria-valuenow", String(Math.round(cut)));
  };
  const size = () => box.style.setProperty("--box", `${box.clientWidth}px`);
  size();
  new ResizeObserver(size).observe(box);

  let dragging = false;
  const move = (e) => {
    const r = box.getBoundingClientRect();
    setCut(((e.clientX - r.left) / r.width) * 100);
  };
  box.addEventListener("pointerdown", (e) => { dragging = true; box.setPointerCapture(e.pointerId); move(e); });
  box.addEventListener("pointermove", (e) => { if (dragging) move(e); });
  const stop = () => { dragging = false; };
  box.addEventListener("pointerup", stop);
  box.addEventListener("pointercancel", stop);
  handle.addEventListener("keydown", (e) => {
    const k = { ArrowLeft: -4, ArrowRight: 4 }[e.key];
    if (k) { e.preventDefault(); setCut(cut + k); }
    if (e.key === "Home") { e.preventDefault(); setCut(8); }
    if (e.key === "End") { e.preventDefault(); setCut(92); }
  });

  // a short intro the first time it scrolls into view: the handle glides from the right edge to the middle
  setCut(50);
  if (!reduceMotion && gsap && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      if (!entries[0].isIntersecting) return;
      io.disconnect();
      const o = { v: 90 };
      setCut(90);
      gsap.to(o, { v: 50, duration: 1.6, ease: "power3.inOut", delay: 0.2, onUpdate: () => { if (!dragging) setCut(o.v); } });
      setTimeout(() => { if (!dragging && Math.abs(cut - 50) > 40) setCut(50); }, 5000);
    }, { threshold: 0.4 });
    io.observe(box);
  }
}
