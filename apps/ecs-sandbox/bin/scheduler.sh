#!/bin/bash
# Start the TaskIQ scheduler process

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$APP_DIR/../.." && pwd)"

export DB_PATH=${DB_PATH:-$PROJECT_ROOT/data/ecs-sandbox.db}
export SANDBOX_SECRET=${SANDBOX_SECRET:-not-secure}
export REDIS_URL=${REDIS_URL:-redis://localhost:6379}

echo "[scheduler] Starting TaskIQ scheduler (Redis=$REDIS_URL)"
cd "$APP_DIR"
uv run taskiq scheduler src.tasks.scheduler:scheduler
