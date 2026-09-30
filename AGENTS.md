# AGENTS.md

Instructions for AI coding agents (GPT, Codex, Claude) working in this repository. People should
start with `HANDOVER.md`.

## Read first

1. `HANDOVER.md`: current state, open items, how to run and deploy.
2. `docs/repo-map.html`: what runs where, and where each part of the code lives.
3. `README.md`: the engine, quickstart, API, module map and design rules.
4. `web/DESIGN.md`: the website's design rules. Read it before any UI change.

## Layout

| Path | What it is |
|---|---|
| `falconverifier/` | Python engine (verify-and-teach loop) and the FastAPI server (`server.py`) |
| `lean/` | Lake project: Mathlib, `Prelude.lean` (`fv_auto`), Arabic pregroup theory, `Graph.lean` |
| `bench/` | Problem sets, generators, `report.py`, and `results/` (committed benchmark runs; treat as data) |
| `web/` | NYU Falcon website source: Vite, React 19, TypeScript, Tailwind v4, Motion, React Router, Phosphor icons |
| `falconverifier/static/` | **Build output** of `web/`, committed. Never edit by hand. |
| `web/public/data/` | **Generated** by `web/scripts/export_data.py`. Never edit by hand. |
| `docs/`, `deploy/`, `tests/`, `.github/workflows/` | Docs and pitch, deployment, pytest suite, CI and image build |

## Commands

```bash
# setup
python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
cd web && npm install && cd ..                      # Node 20.19+ or 22.12+

# run
falconverifier serve                                # site and API on http://localhost:8000
cd web && npm run dev                               # site dev server on :5173, API proxied to :8000

# checks: all must pass before committing (CI runs the Python ones)
ruff check . && ruff format --check .
FV_MEMORY=0 pytest -q                               # Lean integration tests skip unless lean/ is built
cd web && npm run build && npm run lint             # build includes the TypeScript check
```

## Rules

Engine (these must hold for every change):

- The Lean kernel is the only verdict authority. LLM output is never evidence.
- Deterministic fragments (`arabic*.py`) fail closed: return `None` rather than guess.
- A refutation from an LLM translation must survive the faithfulness audit, or it becomes `unknown`.
- World-knowledge premises are `unverified_premise`, never `refuted`.

Website:

- After any change under `web/`, run `npm run build` and commit `web/` and `falconverifier/static/`
  together. The Docker image has no Node stage, so the committed build is what ships.
- After a new benchmark run: `npm run data`, then `npm run build`.
- Every user-facing string is bilingual: `t({ en: '…', ar: '…' })` from `web/src/i18n.tsx`. Arabic
  text containing Western digits goes through `isolateMath()` (`web/src/components/ArabicText.tsx`).
  Lean code renders left-to-right through the `Lean` component.
- Use logical CSS properties (`ms`, `me`, `ps`, `pe`, `start`, `end`, `insetInlineStart`) so layouts
  mirror in Arabic. Mirror directional arrows in RTL (`rtl:rotate-180`); never mirror media icons.
- Color is reserved for kernel verdicts: verified green, refuted vermilion, unknown amber. Tokens
  live in `web/src/styles.css` (`@theme`). No gradients and no new accent colors. `ink-3` is the
  lightest allowed text color (4.5:1 contrast).
- Numbers on the site come from `bench/results/` through the export script. Never type them by hand.
- Animate transform, opacity and filter only. The app is wrapped in
  `MotionConfig reducedMotion="user"`, and `styles.css` has a reduced-motion override; keep both.
- The live demo depends on the server-sent event contract: the event names and payloads emitted by
  `falconverifier/agent.py` and `server.py` are parsed in `web/src/lib/stream.ts` (`eventOf`,
  `applyEvent`). Change both sides together.

Python and git:

- ruff with line length 100 (`pyproject.toml`).
- Never commit secrets. `.env` and `deploy/.env.production` are gitignored.
- Every push to `main` builds and publishes the deployable Docker image. Work on a branch and merge
  when the checks pass.

## Where to change what

| Task | Files |
|---|---|
| A story section | `web/src/story/*.tsx`, composed in `web/src/pages/Story.tsx` |
| The demo chat | `web/src/pages/Demo.tsx`, `web/src/demo/` (`Cards.tsx` holds the answer cards and proof panel) |
| Live streaming and replay | `web/src/lib/stream.ts` |
| The results page | `web/src/pages/Results.tsx`, `web/src/results/` |
| Recorded demo examples | `EXAMPLES` in `web/scripts/export_data.py` |
| A new benchmark run on /results | `ARM_ORDER` in `export_data.py` and `ARM_SET` in `web/src/results/meta.ts`, then `npm run data && npm run build` |
| Verdict labels and colors | `web/src/components/Verdict.tsx`, tokens in `web/src/styles.css` |
| Nav, footer, logo | `web/src/components/Nav.tsx`, `Footer.tsx`, `Mark.tsx`, `web/public/brand/` |
| Server routes | `falconverifier/server.py` (keep the catch-all site route last) |
| Verification logic | `falconverifier/` (module map in `README.md`) |
| Deployment | `Dockerfile`, `deploy/`, `docs/DEPLOY.md` |

## Gotchas

- Motion applies an SVG element's `style` prop only at mount. When a size depends on measured width,
  pass it as an SVG attribute (`fontSize={…}`) instead.
- SVG figures that must stay legible on phones measure their width with `useWidth()`
  (`web/src/lib/useWidth.ts`) and lay out at true pixel size.
- The `html` and `body` base styles in `styles.css` are unlayered on purpose, so a host page's reset
  cannot override them.
- `VITE_STATIC=1 npx vite build --base ./` builds a serverless single page into `web/dist/page`: it
  switches to memory routing, skips the live check and hides replay links that need the server.
- `bench/results/*/latest.json` is gitignored. The export script finds the newest `run_*` folder itself.
- Only the website is branded NYU Falcon. The Python package, the CLI command and the Lean project
  keep the engine name, FalconVerifier (`falconverifier`).
