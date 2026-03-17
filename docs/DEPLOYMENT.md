# Deployment

ecs-sandbox deploys to AWS ECS (Fargate) with EFS for durable storage. Infrastructure is managed via Terraform Cloud.

## Prerequisites

- AWS account with ECS, EFS, ECR, and S3 access
- [Terraform Cloud](https://app.terraform.io) account
- [1Password CLI](https://developer.1password.com/docs/cli/) (`op`) installed and signed in
- [GitHub CLI](https://cli.github.com/) (`gh`) installed and authenticated
- Docker for building images
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)

## First-Time Setup

This section walks through going from a fresh clone to a deployed service with CI/CD.

### 1. Create the GitHub repo

```bash
gh repo create krondor/ecs-sandbox --public --source=. --push
```

This initializes the remote, pushes all code, and sets `origin`.

### 2. Set up 1Password vaults

The project expects two vaults (configured in `.env.vault`):

**`cloud-providers` vault** (shared across projects):

| Item | Field | Description |
|------|-------|-------------|
| `TERRAFORM_CLOUD_API_TOKEN` | credential | TFC API token for workspace management |
| `AWS_CREDENTIALS` | access_key_id | IAM user for ECR/ECS/EFS/S3 |
| `AWS_CREDENTIALS` | secret_access_key | IAM user secret |
| `AWS_CREDENTIALS` | region | e.g. `us-east-1` |
| `CLOUDFLARE_DNS_API_TOKEN` | credential | For DNS zone management |

**`ecs-sandbox-production` vault** (per-stage secrets):

| Item | Field | Description |
|------|-------|-------------|
| `SANDBOX` | credential | Shared API secret (`X-Sandbox-Secret` header value) |
| `ANTHROPIC` | credential | Anthropic API key for the dev CLI agent |

Create these vaults and items in 1Password. The `bin/vault` script reads them at deploy time via the `op://` URI scheme defined in `.env.vault`.

### 3. Create a 1Password Service Account

CI/CD needs headless access to 1Password. Create a service account:

1. Go to 1Password → Settings → Developer → Service Accounts
2. Create an account with read access to both vaults above
3. Copy the service account token

### 4. Add the GitHub secret

```bash
gh secret set OP_SERVICE_ACCOUNT_TOKEN --body "<your-service-account-token>"
```

This is the **only** GitHub secret needed. All other credentials (AWS, TFC, Cloudflare, etc.) are pulled from 1Password at runtime by `bin/vault`.

### 5. Create a GitHub environment

The CD workflow uses a `production` environment for deployment protection:

```bash
gh api repos/krondor/ecs-sandbox/environments/production -X PUT -f wait_timer=0
```

### 6. Bootstrap infrastructure

```bash
# Create TFC org and workspaces
make tfc up

# Deploy ECR repos first (other infra depends on image URIs)
make iac ecr apply

# Build and push initial images
make docker-build
./bin/vault run -- ./bin/docker push ecs-sandbox
./bin/vault run -- ./bin/docker push ecs-sandbox-agent

# Deploy the full stack
make iac production apply
```

### 7. Verify

```bash
# Check the service is running
./bin/vault run -- ./bin/ecs ssh production ecs-sandbox

# Hit the health endpoint
curl https://ecs-sandbox.krondor.org/health
```

After this, CI runs on every push/PR (`ci.yml`: fmt, lint, types, test, docker build) and CD runs on push to `main` (`cd.yml`: terraform apply, build+push to ECR, deploy to ECS).

---

## Infrastructure Overview

```
AWS
├── ECS Cluster (Fargate)
│   ├── ecs-sandbox service (control plane + worker + scheduler)
│   └── ecs-sandbox-cleanup (scheduled task via EventBridge)
├── EFS
│   └── /data/ecs-sandbox.db
│   └── /data/workspaces/{session_id}/
├── ECR
│   ├── ecs-sandbox (control plane image)
│   └── ecs-sandbox-agent (sidecar image)
├── ALB → HTTPS termination → ECS service
├── S3 (optional workspace archival)
└── EventBridge (cleanup cron schedule)
```

## Step 1: Configure Secrets

Set up your 1Password vault with cloud provider credentials. The vault name is configured in `.env.project` as `CLOUD_VAULT`.

Required secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`
- `TFC_TOKEN` (Terraform Cloud API token)

## Step 2: Create Terraform Cloud Workspaces

```bash
make tfc up
```

This creates the TFC organization and workspaces for each environment.

## Step 3: Deploy Container Registry

```bash
make iac container-registry apply
```

Creates ECR repositories for the service images.

## Step 4: Build and Push Images

```bash
# Build images
make docker-build

# Push to ECR (requires AWS auth)
# The bin/docker script handles tagging and pushing
./bin/docker push ecs-sandbox
./bin/docker push ecs-sandbox-agent
```

## Step 5: Deploy Infrastructure

```bash
# Preview changes
make iac production plan

# Apply
make iac production apply
```

This creates:
- VPC, subnets, and security groups
- ECS cluster and service definitions
- EFS filesystem and mount targets
- ALB with HTTPS termination
- EventBridge rule for cleanup cron
- IAM roles and policies

## Step 6: Verify

```bash
# Check ECS service status
aws ecs describe-services --cluster ecs-sandbox --services ecs-sandbox

# Test the endpoint
curl https://ecs-sandbox.krondor.org/sandbox \
  -H "X-Sandbox-Secret: $SANDBOX_SECRET" \
  -X POST -d '{"id": "test-001"}'
```

## ECS Services

| Service | Type | Description |
|---------|------|-------------|
| `ecs-sandbox` | ECS Service | Main control plane (FastAPI on :8000) |
| `worker` | ECS Service | Taskiq background job worker |
| `scheduler` | ECS Service | Taskiq cron scheduler |
| `cleanup` | Scheduled Task | Runs on EventBridge cron to reap stale sessions |

## Configuration

Environment variables are set in the ECS task definition via Terraform:

```env
SANDBOX_SECRET=<from 1Password>
SANDBOX_IMAGE=<ECR URI>:latest
DB_PATH=/data/ecs-sandbox.db
WORKSPACE_BACKEND=efs
EFS_WORKSPACE_ROOT=/data/workspaces
MAX_CONTAINERS=50
DEFAULT_TTL_SECONDS=1800
```

### Cleanup Cron Config

```env
CLEANUP_STALE_THRESHOLD_MINUTES=60
CLEANUP_RETENTION_DAYS=7
CLEANUP_ARCHIVE_TO_S3=true
CLEANUP_S3_BUCKET=ecs-sandbox-archive
```

## Scaling

The service is designed to run as a **single ECS task** initially. Scaling considerations:

- **Container ceiling:** `MAX_CONTAINERS` returns 503 when full — use this as an autoscaling signal
- **SQLite write contention:** Serialized writes are fast for small inserts; only a bottleneck at very high throughput
- **Migration path:** Swap SQLAlchemy connection string from `sqlite+aiosqlite:///...` to `postgresql+asyncpg://...` to enable multi-instance deployment

## Rollback

ECS services use deployment circuit breaker with auto-rollback. If a new deployment fails health checks, ECS automatically rolls back to the previous task definition.
