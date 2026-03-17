# cron-scheduler — Cleanup reaper scheduled task
# Runs on EventBridge cron, marks stale sessions, reaps containers, archives workspaces

locals {
  service = {
    container = {
      cpu    = 256
      memory = 512
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
          name  = "CLEANUP_STALE_THRESHOLD_MINUTES"
          value = "60"
        },
        {
          name  = "CLEANUP_RETENTION_DAYS"
          value = "7"
        },
        {
          name  = "CLEANUP_ARCHIVE_TO_S3"
          value = "false"
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

    # Shares the same EFS volume
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

    # No load balancer — scheduled task
    lb_listener_rule = null

    # This is a scheduled task, not a long-running service
    is_scheduled_task   = true
    schedule_expression = "rate(15 minutes)"
  }
}

output "service" {
  value = local.service
}
