#!/bin/bash
# Start the TaskIQ worker process

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$APP_DIR/../.." && pwd)"

export DB_PATH=${DB_PATH:-$PROJECT_ROOT/data/ecs-sandbox.db}
export SANDBOX_SECRET=${SANDBOX_SECRET:-dev-secret-change-me-in-prod}

echo "[worker] Starting TaskIQ worker"
cd "$APP_DIR"
uv run taskiq worker src.tasks:broker --fs-discover --reload
