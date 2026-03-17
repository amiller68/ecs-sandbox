# background-jobs — Async worker for sandbox command execution
# Shares EFS with ecs-sandbox for DB access, no load balancer needed

locals {
  service = {
    container = {
      cpu    = 512
      memory = 1024
      environment = [
        {
          name  = "DB_PATH"
          value = "/data/ecs-sandbox.db"
        },
        {
          name  = "EFS_WORKSPACE_ROOT"
          value = "/data/workspaces"
        },
        {
          name  = "WORKER_MODE"
          value = "true"
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

    # Shares the same EFS volume as ecs-sandbox
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

    # No load balancer — internal worker only
    lb_listener_rule = null

    # No auto-scaling by default
    auto_scaling = {
      enabled       = false
      min_capacity  = 1
      max_capacity  = 1
      cpu_threshold = 70
    }
  }
}

output "service" {
  value = local.service
}
