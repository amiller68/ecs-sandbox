# -----------------------------------------------------
# STEP 1: Declare service modules
# -----------------------------------------------------
# Each service directory defines its own container config,
# volumes, policies, and scheduling. The service name here
# MUST match: its directory under /apps, its ECR repo name,
# and the key in the service_modules map below.
# -----------------------------------------------------

module "ecs-sandbox" {
  source = "./ecs-sandbox"

  s3_workspace_bucket_arn  = var.s3_workspace_bucket_arn
  s3_workspace_bucket_name = var.s3_workspace_bucket_name
}

module "background-jobs" {
  source = "./background-jobs"
}

module "cron-scheduler" {
  source = "./cron-scheduler"
}

# -----------------------------------------------------
# STEP 2: Register services
# -----------------------------------------------------
locals {
  service_modules = {
    "ecs-sandbox"    = module.ecs-sandbox.service
    "background-jobs" = module.background-jobs.service
    "cron-scheduler"  = module.cron-scheduler.service
  }
}

# -----------------------------------------------------
# STEP 3: Apply defaults + environment overrides
# -----------------------------------------------------

module "service_config" {
  source   = "./_config"
  for_each = local.service_modules

  name        = each.key
  service     = each.value
  environment = var.environment
  override    = try(var.service_configurations[each.key], null)
}

locals {
  services = {
    for name, config in module.service_config : name => config.config
  }
}
