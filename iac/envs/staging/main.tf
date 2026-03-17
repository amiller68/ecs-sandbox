module "common" {
  source = "../common"

  environment = "staging"

  aws_config = {
    aws_region = var.aws_region
    vpc_cidr   = "10.0.0.0/16"

    enable_s3_archival = false

    service_configurations = {
      "ecs-sandbox" = {
        container = {
          cpu    = 1024
          memory = 2048
        }
        auto_scaling = {
          enabled      = true
          min_capacity = 1
          max_capacity = 2
        }
      }
      "background-jobs" = {
        container = {
          cpu    = 512
          memory = 1024
        }
      }
      # cron-scheduler uses defaults (256 CPU, 512 memory)
    }
  }
}
