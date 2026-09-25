# NYU Falcon: handover

Handover of the NYU Falcon website work from the Claude Code cloud session (25 September 2026).
Everything needed to continue is in this repository; nothing lives only in the cloud session.

**NYU Falcon** (team ChaosButterfly) puts the Lean 4 proof kernel between Falcon, TII's
Arabic-native LLM, and the user. Every reasoning step becomes a Lean proposition, the kernel proves
or refutes it, and each refutation goes back to Falcon as a correction. The engine is the Python
package `falconverifier`. The website is new, lives in `web/`, and is branded NYU Falcon.

## Start here

| What | Where |
|---|---|
| **Repo map**: what runs where, deploy steps, where each part of the code lives | `docs/repo-map.html` (open it in a browser) |
| Rules for coding agents (GPT, Codex, Claude) | `AGENTS.md` |
| Project overview, quickstart, API, module map | `README.md` |
| Website: pages, build, design system, product brief | `web/README.md`, `web/DESIGN.md`, `web/PRODUCT.md` |
| Deployment (Docker, Caddy, GHCR) | `docs/DEPLOY.md` |
| Live demo script for the pitch | `docs/PITCH.md` |

Online copies, private to the owner's claude.ai account (open them while signed in, or share them
from the page's Share menu):

- Repo map: https://claude.ai/artifact/SGaPDyEYUTcWb8jXKwqe5v
- The website as a static page (recorded runs only): https://claude.ai/artifact/L4MUXbuYAN1pwP8wVCPCnn

## State at handover

- `main` holds everything. `35f75ad` is PR #1 (engine, benchmarks, docs), `16edc6c` is the NYU Falcon
  website, and the commit adding this file follows.
- CI (ruff and pytest) passed on `16edc6c`. The Docker image workflow for `16edc6c` was still running
  at handover. It publishes `ghcr.io/hw4375-collab/falconverifer:latest`, which is what a deployment
  pulls. Check the Actions tab before deploying.
- Locally in the cloud session: 125 tests passed (11 skipped, the Lean integration tests that need a
  built `lean/`), ruff was clean, and the web build and typecheck were clean.

## Run it locally

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env              # add FALCON_API_KEY for live questions
falconverifier serve              # site and API on http://localhost:8000
```

The built site is committed in `falconverifier/static/`, so this works without Node. Without
`FALCON_API_KEY` and a built Lean project, the demo replays recorded runs only. For live questions,
also build Lean once (Lean `v4.34.0` via elan; see the README Quickstart):

```bash
cd lean && lake exe cache get && lake build && cd ..
```

Working on the website (Node 20.19+ or 22.12+):

```bash
cd web && npm install
npm run dev       # http://localhost:5173, /api and /healthz proxied to :8000
npm run data      # re-export bench/results into web/public/data after a new benchmark run
npm run build     # typecheck, then write falconverifier/static (commit it)
npm run lint
```

Checks CI runs (run them before every push):

```bash
ruff check . && ruff format --check .
FV_MEMORY=0 pytest -q
```

## How the website is wired

- **Pages.** `/` is the story (one real trace, Hamdan's dates, from wrong answer to Lean refutation to
  corrected answer). `/demo` shows a chat with two answers per question: Falcon alone (round 1 of the
  run) and Falcon with Lean. `/results` shows every benchmark run.
- **Build.** `web/src` is built by `npm run build` into `falconverifier/static/`, which is committed
  because the Docker image has no Node stage. `falconverifier/server.py` serves it through a
  catch-all route after the API routes. Never edit `falconverifier/static/` by hand.
- **Data.** `web/scripts/export_data.py` reads the latest run of each arm in `bench/results/` and
  writes `web/public/data/` (`bench.json`, `examples.json`, `traces/*.json`). The nine recorded demo
  examples are listed in `EXAMPLES` in that script. A new benchmark arm also needs a label in
  `web/src/results/meta.ts` (`ARM_SET`) and a place in `ARM_ORDER`.
- **Live mode.** `web/src/lib/stream.ts` posts to `/api/solve/stream` and applies the server-sent
  events (`config`, `status`, `memory`, `round_start`, `student_answer`, `formalized`, `verified`,
  `feedback`, `done`, `saved`, `error`). The demo goes live when `/healthz` reports both
  `lean_project` and `falcon_key`. Recorded runs replay through the same reducer.
- **Static page.** `VITE_STATIC=1 npx vite build --base ./` (in `web/`) writes one self-contained
  page to `web/dist/page` for any static host: memory routing, inlined fonts, recorded runs only.
- **Languages.** English and Arabic with full right-to-left layout. Every string goes through
  `t({ en, ar })`, and digits inside Arabic text go through `isolateMath()`.

## Deploy

One container on a VM, not serverless: Lean needs about 5 GB of Mathlib and 2 to 4 GB of RAM per
concurrent check. The full walkthrough is in `docs/repo-map.html` ("Deploy it") and `docs/DEPLOY.md`.

```bash
# on a fresh Ubuntu 22.04/24.04 server: 4 vCPU, 8 GB RAM, 40 GB disk, ports 80 and 443 open
curl -fsSL https://raw.githubusercontent.com/hw4375-collab/FalconVerifer/main/deploy/install.sh | sudo bash
nano /opt/falconverifier/deploy/.env.production     # DOMAIN, FALCON_API_KEY (optional: FV_ACCESS_TOKEN)
cd /opt/falconverifier
sudo FV_IMAGE=ghcr.io/hw4375-collab/falconverifer:latest bash deploy/install.sh
```

The GHCR package must be public (GitHub, Packages, falconverifer, Change visibility), or the server
needs `docker login ghcr.io`. With no domain, use `<ip-with-dashes>.sslip.io`. The deploy works when
`https://DOMAIN/healthz` shows `lean_project: true` and `falcon_key: true`.

## Open items

1. **Confirm the image.** Check that the Docker image workflow for `16edc6c` finished green before
   the first deploy.
2. **Test live mode end to end.** The cloud session had no Falcon key and no built Lean, so live
   questions were checked only with a mocked server. With a key and `lean/` built, open `/demo` and
   click *Run live: Compound discount* (the answer should end at 576).
3. **Pitch deck branding.** `docs/pitch.html` and `docs/pitch.pdf` still say FalconVerifier and use the
   old title logo (`docs/assets/chaosbutterfly_logo.png`). `python docs/make_pitch.py` rebuilds the
   deck; it reads `bench/results/<arm>/latest.json`, which is gitignored, so copy the latest run's
   `results.json` there first. The slide footers already pick up the new butterfly from
   `web/public/brand/chaosbutterfly-mark.png`.
4. **Older docs.** `docs/WORK_SUMMARY.md` and `docs/talk.html` describe the old UI pages
   (`/benchmark`, `/about`). Those addresses now redirect to `/results` and `/`.
5. **"Caught" vs "detected".** The site counts a wrong answer as caught when Lean refuted a claim in
   round 1 (`wrong_detected_by_lean` in `results.json`). `docs/LOGIC20.md` counts any wrong answer that
   triggered another round, so LOGIC-20 Arabic reads 7 of 11 on the site and 10 of 11 in that doc.

## Demo examples that work

Recorded runs, all Falcon-H1-Arabic 3B unless noted. They are in the demo sidebar and need no server:

| Example | Falcon alone | With Lean | Rounds |
|---|---|---|---|
| Hamdan's dates | 187 | 2291 | 2 |
| Two discounts | 680 | 576 | 2 |
| Order of operations | 75 | 99 | 2 |
| Omar's pens | 315 | 3375 | 3 |
| Who is taller? | لا | نعم | 2 |
| Eight guests shake hands | لا | نعم | 2 |
| Four friends | لا | نعم | 2 |
| A road trip (7B, English) | 431.75 km | 432.25 km | 2 |
| Five classmates | نعم | نعم (proved first time) | 1 |

With a live server, the demo's *Run live* buttons send the two stage examples from `docs/PITCH.md`
(Compound discount, expected 576; Five friends, expected نعم) and two everyday-Arabic prompts
(Restaurant bill, 92.4; Trip day, الثلاثاء).

## Secrets

`FALCON_API_KEY` and any other keys live only in `.env` (local) and `deploy/.env.production`
(server). Both are gitignored. The browser never receives a key.
