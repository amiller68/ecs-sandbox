#!/bin/bash
# Watch ecs-sandbox-agent source files and rebuild Docker image on change
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
AGENT_DIR="$PROJECT_ROOT/apps/ecs-sandbox-agent"
IMAGE_NAME="${SANDBOX_IMAGE:-ecs-sandbox-agent:latest}"

DEBOUNCE_SECONDS=2
LAST_BUILD=0

rebuild() {
    local now
    now=$(date +%s)
    if (( now - LAST_BUILD < DEBOUNCE_SECONDS )); then
        return
    fi
    LAST_BUILD=$now

    echo ""
    echo "[agent-watch] Change detected — rebuilding $IMAGE_NAME..."
    if docker build -q -t "$IMAGE_NAME" "$AGENT_DIR" >/dev/null 2>&1; then
        echo "[agent-watch] Rebuilt $IMAGE_NAME at $(date '+%H:%M:%S')"
    else
        echo "[agent-watch] Build FAILED — retrying with output..."
        docker build -t "$IMAGE_NAME" "$AGENT_DIR"
    fi
}

echo "[agent-watch] Watching $AGENT_DIR for changes to *.py, Dockerfile, requirements.txt"
echo "[agent-watch] Image: $IMAGE_NAME"
echo ""

# Prefer fswatch (macOS), fall back to polling
if command -v fswatch &>/dev/null; then
    fswatch -0 --event Created --event Updated --event Removed \
        --include '\.py$' \
        --include 'Dockerfile' \
        --include 'requirements\.txt' \
        --exclude '.*' \
        --recursive \
        "$AGENT_DIR" | while IFS= read -r -d '' _; do
        rebuild
    done
else
    echo "[agent-watch] fswatch not found, using polling (install fswatch for instant rebuilds)"
    echo "[agent-watch]   brew install fswatch"
    echo ""

    # Polling fallback: check file timestamps every 3 seconds
    get_fingerprint() {
        find "$AGENT_DIR" \( -name '*.py' -o -name 'Dockerfile' -o -name 'requirements.txt' \) \
            -exec stat -f '%m %N' {} + 2>/dev/null | sort
    }

    PREV_FINGERPRINT="$(get_fingerprint)"
    while true; do
        sleep 3
        CURR_FINGERPRINT="$(get_fingerprint)"
        if [ "$CURR_FINGERPRINT" != "$PREV_FINGERPRINT" ]; then
            PREV_FINGERPRINT="$CURR_FINGERPRINT"
            rebuild
        fi
    done
fi
