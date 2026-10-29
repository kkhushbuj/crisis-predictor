import { reduceMotion, gsap } from "./common.js";

/* Wheel and trackpad scrolling glides (Lenis). Skipped for reduced motion. It drives GSAP's clock so scroll-linked
   animations stay in step, and in-page links glide to their section instead of jumping. */
function smoothScroll() {
  const Lenis = window.Lenis;
  if (!Lenis || reduceMotion) return null;
  const lenis = new Lenis({ lerp: 0.1 });
  if (gsap) {
    if (window.ScrollTrigger) lenis.on("scroll", window.ScrollTrigger.update);
    gsap.ticker.add((t) => lenis.raf(t * 1000)); // GSAP's default lag smoothing stays on, so animations resume where they were after a tab switch instead of jumping ahead
  } else {
    const loop = (t) => { lenis.raf(t); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  }
  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    const target = a.getAttribute("href").length > 1 ? document.querySelector(a.getAttribute("href")) : null;
    if (target) a.addEventListener("click", (e) => { e.preventDefault(); lenis.scrollTo(target, { offset: -92 }); });
  });
  return lenis;
}

/* Moving between the home page and the analysis page: the current page fades out first (the next one fades in on its own),
   and the next page starts loading as soon as the pointer is over its link, so the wait is shorter. */
function pageTransitions() {
  const prefetched = new Set();
  const internal = (a) => {
    if (!a || !a.href || a.target || a.hasAttribute("download")) return null;
    const u = new URL(a.href, location.href);
    if (u.origin !== location.origin || u.pathname === location.pathname || u.pathname.startsWith("/api")) return null;
    return u;
  };
  const prefetch = (e) => {
    const u = internal(e.target.closest && e.target.closest("a"));
    if (!u || prefetched.has(u.pathname)) return;
    prefetched.add(u.pathname);
    document.head.append(Object.assign(document.createElement("link"), { rel: "prefetch", href: u.pathname }));
  };
  document.addEventListener("pointerover", prefetch, { passive: true });
  document.addEventListener("focusin", prefetch);
  if (reduceMotion) return;
  document.addEventListener("click", (e) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const u = internal(e.target.closest && e.target.closest("a"));
    if (!u) return;
    e.preventDefault();
    document.documentElement.classList.add("leaving");
    setTimeout(() => { location.href = u.href; }, 260);
  });
  // coming back with the browser's back button can show the old page from memory: make sure it is visible again
  window.addEventListener("pageshow", (e) => { if (e.persisted) document.documentElement.classList.remove("leaving"); });
}

/* Sticky header gets slimmer once you scroll, and a thin bar in the four risk colours shows how far down the page you are.
   The page height is measured only when the window changes size, and the work is done at most once per frame. */
export function initChrome() {
  smoothScroll();
  // looping animations stand still while the tab is hidden, so they carry on from the same place when you come back
  document.addEventListener("visibilitychange", () => document.documentElement.classList.toggle("tab-hidden", document.hidden));
  pageTransitions();
  const head = document.getElementById("site-head");
  const bar = document.getElementById("scroll-progress");
  let max = 0, queued = false;
  const measure = () => { max = document.documentElement.scrollHeight - window.innerHeight; };
  const paint = () => {
    queued = false;
    const y = window.scrollY;
    if (head) head.classList.toggle("scrolled", y > 24);
    if (bar) bar.style.clipPath = `inset(0 ${(100 - (max > 0 ? Math.min(y / max, 1) : 0) * 100).toFixed(2)}% 0 0)`;
  };
  const schedule = () => { if (!queued) { queued = true; requestAnimationFrame(paint); } };
  measure();
  paint();
  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", () => { measure(); schedule(); });
  window.addEventListener("load", () => { measure(); schedule(); });
  if ("ResizeObserver" in window) new ResizeObserver(() => { measure(); schedule(); }).observe(document.body);
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
