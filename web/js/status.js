// Shows a small marker in the top bar of the other pages while an analysis started in this tab is still running,
// and a link to its result once it has finished. The analysis page picks the job up again when you click it.
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
