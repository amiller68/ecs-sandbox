# AWS Infrastructure Module — ecs-sandbox
# Orchestrates networking, load balancer, ECS, S3, and security

locals {
  # TODO (infra-setup): set this to a Route53 hosted zone you control
  hosted_zone_dns_name = "aws.krondor.org"

  # Map service policies to the format expected by the security module
  service_policies = flatten([
    for name, service in module.services.services :
    service.policy != null ? [{
      service_name = name
      role_id      = split("/", module.services_ecs.service_task_roles[name])[1]
      policy = {
        name = "${name}-permissions"
        type = "service"
        definition = {
          Version   = service.policy.Version
          Statement = service.policy.Statement
        }
      }
    }] : []
  ])
}

data "aws_route53_zone" "domain" {
  name = "${local.hosted_zone_dns_name}."
}

# -------------------------------------------------------
# Networking
# -------------------------------------------------------

module "networking" {
  source = "./networking"

  environment        = var.environment
  aws_region         = var.aws_region
  vpc_cidr           = var.vpc_cidr
  availability_zones = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]

  tags = var.tags
}

# -------------------------------------------------------
# Load Balancer
# -------------------------------------------------------

module "loadbalancer" {
  source = "./loadbalancer"

  environment          = var.environment
  hosted_zone_dns_name = local.hosted_zone_dns_name
  vpc_id               = module.networking.vpc_id
  public_subnet_ids    = module.networking.public_subnet_ids
  route53_zone_id      = data.aws_route53_zone.domain.zone_id

  tags = var.tags
}

# -------------------------------------------------------
# S3 — Workspace archival bucket
# -------------------------------------------------------

resource "aws_s3_bucket" "workspaces" {
  count = var.enable_s3_archival ? 1 : 0

  bucket = "${var.environment}-ecs-sandbox-workspaces"

  tags = merge(var.tags, {
    Name = "${var.environment}-ecs-sandbox-workspaces"
  })
}

resource "aws_s3_bucket_lifecycle_configuration" "workspaces" {
  count  = var.enable_s3_archival ? 1 : 0
  bucket = aws_s3_bucket.workspaces[0].id

  rule {
    id     = "expire-old-sessions"
    status = "Enabled"

    expiration {
      days = 30
    }

    filter {
      prefix = "sessions/"
    }
  }
}

# -------------------------------------------------------
# Services — process service definitions
# -------------------------------------------------------

module "services" {
  source = "./services"

  environment            = var.environment
  service_configurations = var.service_configurations

  s3_workspace_bucket_arn  = var.enable_s3_archival ? aws_s3_bucket.workspaces[0].arn : ""
  s3_workspace_bucket_name = var.enable_s3_archival ? aws_s3_bucket.workspaces[0].bucket : ""
}

# -------------------------------------------------------
# ECS Cluster + Services
# -------------------------------------------------------

module "services_ecs" {
  source = "./ecs"

  environment        = var.environment
  aws_region         = var.aws_region
  vpc_id             = module.networking.vpc_id
  private_subnet_ids = module.networking.private_subnet_ids

  alb_security_group_id = module.loadbalancer.security_group_id
  lb_listener_arn       = module.loadbalancer.https_listener_arn

  ecs_cluster = {
    name                      = "ecs-sandbox"
    capacity_providers        = ["FARGATE"]
    default_capacity_provider = "FARGATE"
  }

  services = module.services.services

  tags = var.tags
}

# -------------------------------------------------------
# Security — service-specific IAM policies
# -------------------------------------------------------

module "security" {
  source        = "./security"
  environment   = var.environment
  role_policies = local.service_policies
  tags          = var.tags
}
