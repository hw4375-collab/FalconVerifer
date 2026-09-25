# NYU Falcon website

The NYU Falcon site, served by `falconverifier serve`. It has three pages:

- `/`: the story. A real Falcon trace, from the Arabic question to the Lean refutation to the corrected answer.
- `/demo`: a chat-style demo. Baseline Falcon sits beside Falcon + Lean 4. Recorded runs replay committed
  traces; typed questions run live against `/api/solve/stream` when the server reports Lean and a Falcon key
  on `/healthz`.
- `/results`: every benchmark run in `bench/results/`, with an outcome flow, per-slice accuracy, Lean
  coverage, and every question with a replay link.

```bash
npm install
npm run dev      # http://localhost:5173, proxies /api and /healthz to http://localhost:8000 (set FV_API to change)
npm run data     # re-export bench/results into public/data (bench.json, examples.json, traces/)
npm run build    # typecheck, then build into ../falconverifier/static (committed, so Docker needs no Node)
npm run lint

VITE_STATIC=1 npx vite build --base ./   # one self-contained page in dist/page for static hosting (recorded runs only, no server)
```

Stack: Vite, React 19, TypeScript, Tailwind CSS v4, Motion, React Router, and Phosphor icons. The
design system is documented in `DESIGN.md`, and the product brief it serves in `PRODUCT.md`.

Layout:

```
src/pages/       Story, Demo, Results (Demo and Results are lazy-loaded)
src/story/       the scroll story sections
src/demo/        answer cards, composer, recorded-run sidebar
src/results/     outcome flow, charts, question explorer
src/lib/         data loading, SSE stream + replay engine, types
src/components/  nav, verdict badges, Lean code, dot band, Arabic helpers
scripts/         export_data.py (bench/results to public/data)
```
