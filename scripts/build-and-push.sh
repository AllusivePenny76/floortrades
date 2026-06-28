#!/usr/bin/env bash
# Build a multi-arch (amd64 + arm64) image and push it to GHCR so Umbrel can
# pull it on both Umbrel Home (amd64) and Raspberry Pi (arm64).
#
# Prereqs (one time):
#   docker login ghcr.io -u YOUR_GITHUB_USERNAME    # use a PAT with write:packages
#   docker buildx create --use --name floortrades-builder   # if you don't have a builder
#
# Usage:
#   GH_USER=YOUR_GITHUB_USERNAME VERSION=1.0.0 ./scripts/build-and-push.sh
set -euo pipefail

GH_USER="${GH_USER:?Set GH_USER to your GitHub username}"
VERSION="${VERSION:-1.0.0}"
IMAGE="ghcr.io/${GH_USER}/floortrades"

cd "$(dirname "$0")/.."

echo "Building & pushing ${IMAGE}:${VERSION} (linux/amd64, linux/arm64)…"
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag "${IMAGE}:${VERSION}" \
  --tag "${IMAGE}:latest" \
  --push \
  .

echo
echo "Done. Pin the digest in umbrel/floortrades/docker-compose.yml for reproducibility:"
docker buildx imagetools inspect "${IMAGE}:${VERSION}" | grep -E "Digest|Name" | head -3
