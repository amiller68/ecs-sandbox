#!/bin/bash
# Start the TaskIQ scheduler process

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$APP_DIR/../.." && pwd)"

export DB_PATH=${DB_PATH:-$PROJECT_ROOT/data/ecs-sandbox.db}
export SANDBOX_SECRET=${SANDBOX_SECRET:-dev-secret-change-me-in-prod}

echo "[scheduler] Starting TaskIQ scheduler"
cd "$APP_DIR"
uv run taskiq scheduler src.tasks.scheduler:scheduler
