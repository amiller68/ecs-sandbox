# ecs-sandbox Infrastructure

Terraform modules for deploying ecs-sandbox to AWS ECS (Fargate).

## Architecture

```
iac/
├── bin/tf                      # Terraform wrapper script
├── envs/
│   ├── common/                 # Shared module (all envs go through here)
│   ├── ecr/                    # ECR repositories (shared across envs)
│   ├── staging/                # Staging environment config
│   └── production/             # Production environment config
└── modules/aws/
    ├── ecr/                    # ECR repository management
    ├── ecs/                    # ECS cluster, tasks, services, EFS, EventBridge
    ├── loadbalancer/           # ALB + HTTPS + Route53
    ├── networking/             # VPC, subnets, NAT gateway
    ├── security/               # IAM policy bindings
    └── services/               # Service definitions
        ├── _defaults/          # Default container/service config
        ├── _config/            # Merge logic (defaults + overrides)
        ├── ecs-sandbox/        # Main API service
        ├── background-jobs/    # Async worker
        └── cron-scheduler/     # Cleanup reaper (EventBridge scheduled)
```

## Services

| Service | Type | Port | Description |
|---------|------|------|-------------|
| **ecs-sandbox** | ECS Service + ALB | 8000 | FastAPI control plane, manages sandbox containers |
| **background-jobs** | ECS Service | 8000 | Async worker for command execution |
| **cron-scheduler** | EventBridge Scheduled Task | — | Cleanup reaper: marks stale sessions, removes containers |
| **ecs-sandbox-agent** | Docker image (not ECS) | 2222 | Sidecar inside each sandbox container |

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform >= 1.0.0
3. S3 bucket + DynamoDB table for state: `ecs-sandbox-tf-state` / `ecs-sandbox-tf-state-lock`
4. Route53 hosted zone (default: `aws.krondor.org`)

## Usage

```bash
# ECR repositories (run first, once)
./bin/tf ecr init
./bin/tf ecr plan
./bin/tf ecr apply

# Staging
./bin/tf staging terraform init
./bin/tf staging terraform plan
./bin/tf staging terraform apply

# Production
./bin/tf production terraform init
./bin/tf production terraform plan
./bin/tf production terraform apply
```

## Adding a New Service

1. Create `iac/modules/aws/services/<name>/main.tf` (copy from `ecs-sandbox/`)
2. Add module declaration in `iac/modules/aws/services/main.tf`
3. Add to `local.service_modules` map in the same file
4. Add to ECR services list in `iac/envs/ecr/main.tf`

## Configuration

Environment-specific overrides go in `envs/<env>/main.tf` under `service_configurations`. Each service can override CPU, memory, auto-scaling, and environment variables without touching the module definitions.
