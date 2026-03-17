#!/usr/bin/env bash
# Manage a local Redis container for development

set -o errexit
set -o nounset

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$PROJECT_ROOT/bin/utils"

REDIS_CONTAINER_NAME="${PROJECT_NAME:-ecs-sandbox}-redis"
REDIS_VOLUME_NAME="${PROJECT_NAME:-ecs-sandbox}-redis-data"
REDIS_PORT=6379
REDIS_IMAGE_NAME=redis:7-alpine

CONTAINER_RUNTIME="docker"
if ! which docker &>/dev/null && which podman &>/dev/null; then
    CONTAINER_RUNTIME="podman"
fi

function check_runtime {
    if ! $CONTAINER_RUNTIME ps &>/dev/null; then
        echo -e "${RED}Error: $CONTAINER_RUNTIME is not running. Please start it first.${NC}"
        exit 1
    fi
}

function up {
    check_runtime

    print_header "Starting Redis"

    # Check if container exists (running or stopped)
    if $CONTAINER_RUNTIME ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        if $CONTAINER_RUNTIME ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NAME}$"; then
            echo -e "${GREEN}Redis container is already running.${NC}"
            return 0
        else
            echo "Starting existing Redis container..."
            $CONTAINER_RUNTIME start $REDIS_CONTAINER_NAME
            sleep 2
            echo -e "${GREEN}Redis started!${NC}"
            return 0
        fi
    fi

    # Container doesn't exist - create and start it
    echo "Creating new Redis container..."
    $CONTAINER_RUNTIME pull $REDIS_IMAGE_NAME
    $CONTAINER_RUNTIME volume create $REDIS_VOLUME_NAME || true

    $CONTAINER_RUNTIME run \
        --name $REDIS_CONTAINER_NAME \
        --publish $REDIS_PORT:6379 \
        --volume $REDIS_VOLUME_NAME:/data \
        --health-cmd="redis-cli ping || exit 1" \
        --health-interval=5s \
        --health-timeout=5s \
        --health-retries=5 \
        --detach \
        $REDIS_IMAGE_NAME \
        redis-server --appendonly yes

    echo -e "${YELLOW}Waiting for Redis to be ready...${NC}"
    sleep 2
    echo -e "${GREEN}Redis started on localhost:${REDIS_PORT}${NC}"
}

function down {
    check_runtime
    print_header "Cleaning Redis Container"

    $CONTAINER_RUNTIME stop $REDIS_CONTAINER_NAME 2>/dev/null || true
    $CONTAINER_RUNTIME rm -f $REDIS_CONTAINER_NAME 2>/dev/null || true
    $CONTAINER_RUNTIME volume rm -f $REDIS_VOLUME_NAME 2>/dev/null || true

    echo -e "${GREEN}Redis cleaned up.${NC}"
}

function endpoint {
    echo "redis://localhost:${REDIS_PORT}"
}

function status {
    check_runtime
    if $CONTAINER_RUNTIME ps | grep -q "$REDIS_CONTAINER_NAME"; then
        echo -e "${GREEN}Redis is running on localhost:${REDIS_PORT}${NC}"
    else
        echo -e "${RED}Redis is not running. Start with: $0 up${NC}"
    fi
}

function help {
    echo "Usage: $0 [up|down|endpoint|status|help]"
}

CMD=${1:-help}
shift || true
case "$CMD" in
    up|down|endpoint|status|help) $CMD "$@" ;;
    *) echo -e "${RED}Unknown command: $CMD${NC}"; help; exit 1 ;;
esac
