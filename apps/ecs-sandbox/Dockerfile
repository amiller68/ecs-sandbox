# Build context is the repository root
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime

WORKDIR /app

# Install system dependencies (Docker CLI for container management)
RUN apt-get update && apt-get install -y \
    gcc \
    make \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy Python workspace files
COPY pyproject.toml ./pyproject.toml

# Copy packages
COPY packages/ecs-sandbox-client/ ./packages/ecs-sandbox-client/

# Copy app
COPY apps/ecs-sandbox/pyproject.toml ./apps/ecs-sandbox/pyproject.toml
COPY apps/ecs-sandbox/src/ ./apps/ecs-sandbox/src/

# Sync workspace
RUN uv sync --all-packages

# Create data directories
RUN mkdir -p /data/workspaces

# Create startup script
RUN echo '#!/bin/bash\n\
set -ex\n\
echo "Starting ecs-sandbox..."\n\
echo "Applying database migrations..."\n\
cd /app/apps/ecs-sandbox\n\
uv run python -c "from src.db.connection import apply_migrations; import asyncio; asyncio.run(apply_migrations())"\n\
echo "Starting server..."\n\
export LISTEN_ADDRESS=0.0.0.0\n\
export LISTEN_PORT=8000\n\
export DEBUG=False\n\
uv run python -m src\n\
' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000

# CMD allows override for worker/scheduler roles
CMD ["/app/start.sh"]
