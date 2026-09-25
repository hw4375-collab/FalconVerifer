# Deploying FalconVerifier as a public website

The service is a single FastAPI process that shells out to a local Lean 4 + Mathlib
checkout. Lean is the heavy part (≈5 GB of cached oleans, 2–4 GB RAM per concurrent
check), so the deployment target is **one container on a VM**, not a serverless
function.

## What you need

| Item | Notes |
| --- | --- |
| Ubuntu VPS | ≥ 4 vCPU, 8 GB RAM, 40 GB disk (Hetzner CPX31, DO 8 GB, AWS t3.large, GCP e2-standard-2 all work) |
| DNS name | An `A` record → server IP. No domain? use `<ip-with-dashes>.sslip.io` (free, resolves automatically) |
| Falcon API key | The TII Open WebUI JWT; lives only in `deploy/.env.production` on the server |

## Install (≈ 15 min, most of it downloading Mathlib)

```bash
ssh root@SERVER
curl -fsSL https://raw.githubusercontent.com/hw4375-collab/FalconVerifer/main/deploy/install.sh | bash
nano /opt/falconverifier/deploy/.env.production     # DOMAIN=..., FALCON_API_KEY=...
bash /opt/falconverifier/deploy/install.sh           # builds the image, starts app + Caddy
```

Caddy obtains a Let's Encrypt certificate for `DOMAIN` automatically, so the UI is at
`https://DOMAIN/` and the API at `https://DOMAIN/api/...`. Ports 80/443 must be open in
the provider firewall.

Upgrade later: `cd /opt/falconverifier && git pull && bash deploy/install.sh`.

### Skip the Mathlib build: pull the CI image

`.github/workflows/docker.yml` publishes `ghcr.io/hw4375-collab/falconverifer:latest` (and
`:sha-…`, `:vX.Y.Z` on tags) on every push to `main`. On the server:

```bash
FV_IMAGE=ghcr.io/hw4375-collab/falconverifer:latest bash deploy/install.sh
```

The package must be public (GitHub → Packages → falconverifer → Change visibility) or the
server needs `docker login ghcr.io` with a read-only PAT.

## Runtime guards (env vars, see `deploy/.env.production.example`)

- `FV_MAX_CONCURRENT` — Lean loops that may run at once (semaphore; extra requests queue
  and the UI shows "queued").
- `FV_RATE_PER_HOUR` — solves per client IP per hour (429 beyond that).
- `FV_MAX_PROBLEM_CHARS` — reject oversized inputs.
- `FV_ACCESS_TOKEN` — when set, every API call needs header `X-FV-Token`; the web UI asks
  for it once and stores it in `localStorage`. Use this for a semi-private hackathon demo.
- `FV_STUDENT_MODELS` — allow-list of student models a client may request.
- `FV_GITHUB_REPO` / `FV_GITHUB_REF` / `FV_GITHUB_BLOB_BASE` — where the `/benchmark` page
  links its evidence (problems, `results.json`, traces, code). Defaults to the current git
  branch of the checkout, falling back to `main` — set `FV_GITHUB_REF=main` inside Docker.

`GET /healthz` reports Lean availability, key presence and free workers; Docker uses it
as the container health check.

## Public API (what a Falcon plugin or any client calls)

```http
POST /api/solve/stream           # SSE events: config, round_start, student_answer,
                                 #   formalized, verified, feedback, done, saved, error
POST /api/solve                  # same loop, one JSON AgentTrace when finished
POST /api/check                  # {"props": ["(2:ℕ) + 2 = 4", ...]} -> Lean verdicts only
GET  /api/config                 # configured models / providers
GET  /api/bench/latest           # summary per benchmark run (home-page table)
GET  /api/bench/runs             # full results + per-problem rows + GitHub evidence links
GET  /api/bench/trace/{run_dir}/{run}/{problem_id}   # one committed assurance trace
GET  /healthz
```

Pages: `/` verifier, `/benchmark` charts + evidence, `/about` method; `/?trace=<run_dir>/<run>/<id>`
replays a committed benchmark trace through the live UI.

Request body for `/api/solve*`:

```json
{"problem": "ما هو ناتج ١٧ × ٢٣؟", "rounds": 3,
 "formalizer": "falcon", "student_model": "falcon-h1-arabic-3b-instruct"}
```

Example:

```bash
curl -s https://DOMAIN/api/solve -H 'Content-Type: application/json' \
  -H "X-FV-Token: $FV_ACCESS_TOKEN" \
  -d '{"problem":"What is 17 * 23?","rounds":2}' | jq '.status, .rounds[-1].answer.final_answer'
```

## Alternatives

- **Fly.io / Railway / Render**: build the same `Dockerfile`; set the env vars in the
  dashboard; pick a machine with ≥ 8 GB RAM. Drop the Caddy service (they terminate TLS).
- **Local only**: `falconverifier serve` as in the README; `docker compose` also works on
  a laptop with `DOMAIN=localhost` (self-signed certificate).

## Storage

Assurance traces are written to `/app/runs` (a named Docker volume). They are useful for
post-hoc audit but nothing in the app depends on them; wiping the volume is safe.
