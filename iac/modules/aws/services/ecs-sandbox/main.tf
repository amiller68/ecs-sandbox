# ecs-sandbox — Main FastAPI control plane service
# Manages sandbox containers, needs EFS for SQLite + workspaces

locals {
  service = {
    container = {
      cpu    = 1024
      memory = 2048
      environment = [
        {
          name  = "DB_PATH"
          value = "/data/ecs-sandbox.db"
        },
        {
          name  = "WORKSPACE_BACKEND"
          value = "efs"
        },
        {
          name  = "EFS_WORKSPACE_ROOT"
          value = "/data/workspaces"
        },
        {
          name  = "MAX_CONTAINERS"
          value = "50"
        },
        {
          name  = "DEFAULT_TTL_SECONDS"
          value = "1800"
        },
        {
          name  = "SANDBOX_IMAGE"
          value = "ecs-sandbox-agent:latest"
        },
        {
          name  = "SANDBOX_MEMORY_LIMIT"
          value = "512m"
        },
        {
          name  = "SANDBOX_CPU_LIMIT"
          value = "0.5"
        },
        {
          name  = "SANDBOX_PIDS_LIMIT"
          value = "128"
        },
        {
          name  = "S3_WORKSPACE_BUCKET"
          value = var.s3_workspace_bucket_name
        }
      ]
      mount_points = [
        {
          sourceVolume  = "data"
          containerPath = "/data"
          readOnly      = false
        }
      ]
    }

    # EFS volume for SQLite DB + workspaces
    volumes = [
      {
        name = "data"
        efs = {
          creation_token   = "ecs-sandbox-data"
          encrypted        = true
          performance_mode = "generalPurpose"
          throughput_mode  = "bursting"
          root_directory   = "/data"
          owner_uid        = "1000"
          owner_gid        = "1000"
          permissions      = "755"
        }
      }
    ]

    # This service is exposed via ALB
    lb_listener_rule = {
      path_pattern = ["/sandbox/*", "/health"]
    }

    # S3 access for workspace archival
    policy = var.s3_workspace_bucket_arn != "" ? {
      Version = "2012-10-17"
      Statement = [
        {
          Effect = "Allow"
          Action = [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:ListBucket"
          ]
          Resource = [
            var.s3_workspace_bucket_arn,
            "${var.s3_workspace_bucket_arn}/*"
          ]
        }
      ]
    } : null
  }
}

output "service" {
  value = local.service
}
