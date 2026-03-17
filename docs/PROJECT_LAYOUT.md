# Project Layout

## Root

```
ecs-sandbox/
├── apps/                          # Application services
│   ├── ecs-sandbox/               # FastAPI control plane
│   ├── ecs-sandbox-agent/         # Sidecar for sandbox containers
│   └── dev-cli/                   # Development CLI + test agent
├── packages/                      # Shared libraries
│   └── ecs-sandbox-client/        # Typed Python client
├── iac/                           # Terraform infrastructure
│   ├── envs/                      # Environment-specific configs
│   │   ├── common/                # Shared module
│   │   ├── staging/
│   │   ├── production/
│   │   └── aws-ecr/               # Container registry
│   └── modules/aws/               # AWS modules
│       ├── ecs/                   # ECS cluster, services, tasks
│       ├── networking/            # VPC, subnets
│       ├── loadbalancer/          # ALB, ACM, Route53
│       ├── efs/                   # EFS filesystem
│       ├── ecr/                   # ECR repositories
│       ├── s3/                    # S3 buckets
│       └── services/              # Service definitions
├── bin/                           # Scripts
│   ├── dev                        # Tmux dev server orchestration
│   ├── vault                      # 1Password secrets access
│   ├── iac                        # Terraform wrapper
│   └── tfc                        # Terraform Cloud management
├── docs/                          # Documentation
├── .claude/                       # Claude Code config + skills
├── Makefile                       # Root orchestration
├── pyproject.toml                 # uv workspace root
├── docker-compose.yml             # Local dev stack
├── .env.project                   # Project config
└── .gitignore
```

## Entry Points

| Component | Entry Point | Command |
|-----------|-------------|---------|
| Control plane | `apps/ecs-sandbox/src/main.py` | `make dev` or `uvicorn` |
| Worker | `apps/ecs-sandbox/src/tasks/` | `taskiq worker` |
| Scheduler | `apps/ecs-sandbox/src/tasks/scheduler.py` | `taskiq scheduler` |
| Cleanup | `apps/ecs-sandbox/src/services/cleanup.py` | Scheduled ECS task |
| Sidecar | `apps/ecs-sandbox-agent/agent.py` | Runs inside sandbox containers |
| Dev CLI | `apps/dev-cli/src/dev_cli/main.py` | `uv run dev-cli` |
| Client | `packages/ecs-sandbox-client/src/ecs_sandbox/client.py` | Import as library |

## Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | uv workspace root, dev dependencies |
| `apps/*/pyproject.toml` | Per-app dependencies and build config |
| `packages/*/pyproject.toml` | Per-package dependencies |
| `docker-compose.yml` | Local dev stack definition |
| `.env.project` | Project name, DNS, service list |
| `Makefile` | Root-level make targets |
| `apps/*/Makefile` | Per-app make targets |
| `jig.toml` | Agent spawn configuration |
