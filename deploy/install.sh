#!/usr/bin/env bash
# One-shot install on a fresh Ubuntu 22.04/24.04 VPS (>= 4 vCPU, 8 GB RAM, 40 GB disk).
#   curl -fsSL https://raw.githubusercontent.com/hw4375-collab/FalconVerifer/main/deploy/install.sh | sudo bash
set -euo pipefail

REPO=${REPO:-https://github.com/hw4375-collab/FalconVerifer.git}
BRANCH=${BRANCH:-main}
DIR=${DIR:-/opt/falconverifier}

if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi

if [ ! -d "$DIR/.git" ]; then
  git clone --branch "$BRANCH" "$REPO" "$DIR"
else
  git -C "$DIR" pull --ff-only
fi

cd "$DIR"
if [ ! -f deploy/.env.production ]; then
  cp deploy/.env.production.example deploy/.env.production
  echo ">>> Edit $DIR/deploy/.env.production (DOMAIN, FALCON_API_KEY) then re-run this script."
  exit 0
fi

# FV_IMAGE=ghcr.io/hw4375-collab/falconverifer:latest pulls the CI-built image (minutes)
# instead of building Mathlib locally (15-20 min).
if [ -n "${FV_IMAGE:-}" ]; then
  FV_IMAGE="$FV_IMAGE" docker compose -f deploy/docker-compose.yml --env-file deploy/.env.production up -d --pull always --no-build
else
  docker compose -f deploy/docker-compose.yml --env-file deploy/.env.production up -d --build
fi
echo ">>> Waiting for the app to become healthy..."
for _ in $(seq 1 60); do
  if docker compose -f deploy/docker-compose.yml --env-file deploy/.env.production exec -T app \
       curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
    echo ">>> Up: https://$(grep -E '^DOMAIN=' deploy/.env.production | cut -d= -f2)"
    exit 0
  fi
  sleep 5
done
echo "app did not become healthy; see: docker compose -f deploy/docker-compose.yml logs app"
exit 1
