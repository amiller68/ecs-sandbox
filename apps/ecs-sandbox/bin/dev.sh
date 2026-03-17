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
export SANDBOX_SECRET=${SANDBOX_SECRET:-not-secure}
export SANDBOX_IMAGE=${SANDBOX_IMAGE:-ecs-sandbox-agent:latest}
export REDIS_URL=${REDIS_URL:-redis://localhost:6379}

# Ensure data directory exists
mkdir -p "$(dirname "$DB_PATH")"

# Build sandbox agent image if missing or source changed
AGENT_DIR="$PROJECT_ROOT/apps/ecs-sandbox-agent"
if ! docker image inspect "$SANDBOX_IMAGE" &>/dev/null; then
    echo "[dev] Building $SANDBOX_IMAGE (not found locally)..."
    docker build -t "$SANDBOX_IMAGE" "$AGENT_DIR"
else
    # Rebuild if any source files are newer than the image
    IMAGE_CREATED=$(docker image inspect "$SANDBOX_IMAGE" --format '{{.Created}}' 2>/dev/null)
    IMAGE_TS=$(date -jf "%Y-%m-%dT%H:%M:%S" "${IMAGE_CREATED%%.*}" +%s 2>/dev/null || date -d "${IMAGE_CREATED%%.*}" +%s 2>/dev/null || echo 0)
    NEWEST_SRC=$(find "$AGENT_DIR" -name '*.py' -o -name 'Dockerfile' -o -name 'requirements.txt' | xargs stat -f '%m' 2>/dev/null | sort -rn | head -1 || echo 0)
    if [ "${NEWEST_SRC:-0}" -gt "${IMAGE_TS:-0}" ]; then
        echo "[dev] Rebuilding $SANDBOX_IMAGE (source changed)..."
        docker build -t "$SANDBOX_IMAGE" "$AGENT_DIR"
    fi
fi

echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║  ecs-sandbox Dev Server Starting                       ║"
echo "╠════════════════════════════════════════════════════════╣"
printf "║  Server:   %-43s ║\n" "http://localhost:${LISTEN_PORT}"
printf "║  Terminal: %-43s ║\n" "http://localhost:${LISTEN_PORT}/web"
printf "║  Token:    %-43s ║\n" "${SANDBOX_SECRET}"
printf "║  DB:       %-43s ║\n" "${DB_PATH}"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

cd "$APP_DIR"
uv run python -m src
