# Common environment module
# Conditionally deploys AWS infrastructure based on config

module "aws" {
  source = "../../modules/aws"
  count  = var.aws_config != null ? 1 : 0

  environment = var.environment
  aws_region  = var.aws_config.aws_region
  vpc_cidr    = var.aws_config.vpc_cidr

  enable_s3_archival     = var.aws_config.enable_s3_archival
  service_configurations = var.aws_config.service_configurations

  tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = local.project_name
    },
    var.aws_config.tags
  )
}
