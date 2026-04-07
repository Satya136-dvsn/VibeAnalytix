#!/bin/sh
set -eu

# Simple rollback helper for Docker Compose production.
# Usage:
#   ./scripts/rollback.sh <git-ref>
# Example:
#   ./scripts/rollback.sh v1.0.3

TARGET_REF=${1:-}
if [ -z "$TARGET_REF" ]; then
  echo "Usage: $0 <git-ref>"
  exit 1
fi

echo "[rollback] Fetching latest refs..."
git fetch --all --tags

echo "[rollback] Checking out $TARGET_REF"
git checkout "$TARGET_REF"

echo "[rollback] Rebuilding and restarting production stack"
docker compose -f docker-compose.prod.yml up -d --build

echo "[rollback] Completed"
