# Running and deploying the CrisisPredictor website

The website (`web/`) is plain HTML, CSS and JavaScript. A small FastAPI backend (`api/main.py`) serves it
and runs the existing scoring pipeline. No scoring logic lives in the web layer.

## Run it on your computer

```bash
pip install -r requirements-web.txt
uvicorn api.main:app --port 8000
```

Open http://localhost:8000. You need a `.env` file in the project root with `OPENAI_API_KEY`,
`FRED_API_KEY` and (optionally) `TAVILY_API_KEY`.

## Live deployment (Oracle Cloud)

The site is live at https://145-241-213-220.sslip.io on an Oracle Cloud Always Free ARM server
(Ubuntu 22.04, 4 CPUs, 24 GB RAM). The setup is:

- The project lives in `~/crisis` with its own Python virtual environment and a `.env` file that only exists on the server.
- A systemd service (`crisis.service`) runs `uvicorn api.main:app --host 127.0.0.1 --port 8000` and restarts it on failure or reboot.
- Caddy serves HTTPS for the free `sslip.io` name and proxies to port 8000 (streaming is not buffered, long timeouts).
- The Oracle security list allows ports 22, 80 and 443.
- One full analysis takes about 45 seconds and the app peaks at about 230 MB of memory.

## Deploy on Render

1. Push the project to GitHub (the `.env` file is already in `.gitignore`).
2. In Render choose New, then Blueprint, and pick the repository. It reads `render.yaml`.
3. In the service's Environment tab, set `OPENAI_API_KEY`, `FRED_API_KEY` and `TAVILY_API_KEY`.
4. Deploy. `/healthz` should report all three keys as `true`.

Things to know:
- `render.yaml` uses the `starter` plan because the free plan has 512 MB of memory, which is tight for
  FAISS and LangChain, and it goes to sleep when idle. This setup has not been tried on Render yet, so
  check the first deploy logs.
- Every analysis costs a few cents of OpenAI usage. Limits are set in `render.yaml`:
  6 analyses per visitor per hour and 150 per day for the whole site. Lower them if you like.
- Visitor history is kept only for the current visit (browser tab) and cleared when the tab is closed. Nothing is stored on the server.
- Two analyses run at the same time (`MAX_PARALLEL_ANALYSES`, default 2; use 1 on a small server). Others wait, and a busy message appears if more than 3 are waiting.

## Where things live

| What | Where |
|---|---|
| Risk levels (Calm, Elevated, Stress, Crisis) | `REGIMES` in `tools/scoring_tools.py`. The website reads them from `/api/config`. |
| Category weights | `CATEGORY_WEIGHTS` in `tools/scoring_tools.py` |
| Alarm switch (ON at 55) | `graph/crisis_graph.py`, `status = "ON" if composite >= 55` |
| News alert thresholds | `api/main.py` (`NEWS_ALERT_HIGH`, `NEWS_ALERT_MODERATE`) |
| Evidence on the landing page | `web/data/evidence.json`, rebuilt by `python backtest/build_web_evidence.py` |

If you change the weights or the cutoffs, re-run `python backtest/build_web_evidence.py` so the landing
page numbers match the live model.
