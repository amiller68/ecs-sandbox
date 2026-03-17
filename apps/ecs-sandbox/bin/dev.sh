#!/bin/bash
# Start the FastAPI dev server with hot reload

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$APP_DIR/../.." && pwd)"

export DEV_MODE=True
export DEBUG=True
export LISTEN_ADDRESS=0.0.0.0
export LISTEN_PORT=${LISTEN_PORT:-8000}
export DB_PATH=${DB_PATH:-$PROJECT_ROOT/data/ecs-sandbox.db}
export SANDBOX_SECRET=${SANDBOX_SECRET:-dev-secret-change-me-in-prod}

# Ensure data directory exists
mkdir -p "$(dirname "$DB_PATH")"

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ecs-sandbox Dev Server Starting                       ║"
echo "╠════════════════════════════════════════════════════════╣"
printf "║  Server:  %-44s ║\n" "http://localhost:${LISTEN_PORT}"
printf "║  DB:      %-44s ║\n" "${DB_PATH}"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

cd "$APP_DIR"
uv run python -m src
