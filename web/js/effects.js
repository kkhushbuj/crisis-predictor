import { reduceMotion, gsap } from "./common.js";

/* Sticky header gets slimmer once you scroll, and a thin bar shows how far down the page you are. */
export function initChrome() {
  const head = document.getElementById("site-head");
  const bar = document.getElementById("scroll-progress");
  const update = () => {
    const y = window.scrollY;
    if (head) head.classList.toggle("scrolled", y > 24);
    if (bar) {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.transform = `scaleX(${max > 0 ? Math.min(y / max, 1) : 0})`;
    }
  };
  update();
  window.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
}

/* Items fade and rise once as they enter the screen (done with CSS transitions, so it is smooth and cheap). */
export function revealOnScroll(selector, { step = 0.09, group = 4 } = {}) {
  const items = [...document.querySelectorAll(selector)];
  if (!items.length) return;
  if (reduceMotion || !("IntersectionObserver" in window)) {
    items.forEach((i) => i.classList.add("in"));
    return;
  }
  items.forEach((i, k) => {
    i.setAttribute("data-fade", "");
    i.style.transitionDelay = `${(k % group) * step}s`;
  });
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("in");
        io.unobserve(e.target);
      }
    });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
  items.forEach((i) => io.observe(i));
}

/* Counts a number up from zero. The final value is always written, even if the animation is skipped. */
export function countUp(node, to, { decimals = 0, duration = 1.5, delay = 0 } = {}) {
  const final = () => { node.textContent = to.toFixed(decimals); };
  if (reduceMotion || !gsap) { final(); return; }
  node.textContent = (0).toFixed(decimals);
  const o = { v: 0 };
  gsap.to(o, {
    v: to, duration, delay, ease: "power3.out",
    onUpdate: () => { node.textContent = o.v.toFixed(decimals); },
    onComplete: final,
  });
  setTimeout(final, (delay + duration) * 1000 + 4000); // safety net
}

/* Main buttons drift gently toward the cursor. Skipped on touch screens and for reduced motion. */
export function magnetic(nodes, strength = 0.3) {
  if (reduceMotion || !gsap || window.matchMedia("(pointer: coarse)").matches) return;
  nodes.forEach((node) => {
    const xTo = gsap.quickTo(node, "x", { duration: 0.5, ease: "power3.out" });
    const yTo = gsap.quickTo(node, "y", { duration: 0.5, ease: "power3.out" });
    node.addEventListener("pointermove", (e) => {
      const r = node.getBoundingClientRect();
      xTo((e.clientX - (r.left + r.width / 2)) * strength);
      yTo((e.clientY - (r.top + r.height / 2)) * strength);
    });
    node.addEventListener("pointerleave", () => { xTo(0); yTo(0); });
  });
}
