module "common" {
  source = "../common"

  environment = "production"

  aws_config = {
    aws_region = var.aws_region
    vpc_cidr   = "10.0.0.0/16"

    enable_s3_archival = true

    service_configurations = {
      "ecs-sandbox" = {
        container = {
          cpu    = 2048
          memory = 4096
        }
        auto_scaling = {
          enabled      = true
          min_capacity = 2
          max_capacity = 5
        }
      }
      "background-jobs" = {
        container = {
          cpu    = 1024
          memory = 2048
        }
        desired_count = 2
      }
      # cron-scheduler runs on EventBridge, no scaling needed
    }
  }
}
