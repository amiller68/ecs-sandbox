provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type        = string
  description = "AWS region for ECR repositories"
  default     = "us-east-1"
}

# All services that need ECR repositories
# Must match the service name in the monorepo apps/ directory
locals {
  services = [
    "ecs-sandbox",
    "ecs-sandbox-agent",
    "background-jobs",
    "cron-scheduler",
  ]
}

module "ecr" {
  source = "../../modules/aws/ecr"

  repository_names = local.services

  lifecycle_policies = {
    for service in local.services :
    "${service}" => var.default_lifecycle_policy
  }

  tags = {
    Project   = "ecs-sandbox"
    ManagedBy = "terraform"
  }
}
