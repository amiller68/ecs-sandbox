# Get defaults for this specific service
module "defaults" {
  source      = "../_defaults"
  name        = var.name
  environment = var.environment
}

locals {
  # Start with service-specific config and apply defaults
  service_with_defaults = {
    container = {
      name       = var.name
      repository = module.defaults.container.repository
      port       = module.defaults.container.port
      tag        = module.defaults.container.tag

      cpu    = coalesce(var.service.container.cpu, module.defaults.container.cpu)
      memory = coalesce(var.service.container.memory, module.defaults.container.memory)

      environment  = concat(coalesce(var.service.container.environment, []), module.defaults.container.environment)
      secrets      = var.service.container.secrets
      mount_points = var.service.container.mount_points
      health_check = module.defaults.container.health_check
    }

    desired_count = coalesce(var.service.desired_count, module.defaults.service.desired_count)

    auto_scaling          = coalesce(try(var.service.auto_scaling.enabled, null), module.defaults.service.auto_scaling)
    min_capacity          = coalesce(try(var.service.auto_scaling.min_capacity, null), module.defaults.service.min_capacity)
    max_capacity          = coalesce(try(var.service.auto_scaling.max_capacity, null), module.defaults.service.max_capacity)
    scaling_cpu_threshold = coalesce(try(var.service.auto_scaling.cpu_threshold, null), module.defaults.service.scaling_cpu_threshold)

    # Use service-level lb_listener_rule if explicitly set, otherwise use defaults
    # Services that set lb_listener_rule = null explicitly get no load balancer
    lb_listener_rule = var.service.lb_listener_rule

    volumes = var.service.volumes

    is_scheduled_task   = var.service.is_scheduled_task
    schedule_expression = var.service.schedule_expression

    policy = var.service.policy
  }

  # Apply any environment-specific overrides
  config = {
    container = {
      name       = local.service_with_defaults.container.name
      repository = local.service_with_defaults.container.repository
      port       = local.service_with_defaults.container.port
      tag        = local.service_with_defaults.container.tag

      cpu    = coalesce(try(var.override.container.cpu, null), local.service_with_defaults.container.cpu)
      memory = coalesce(try(var.override.container.memory, null), local.service_with_defaults.container.memory)

      environment  = concat(local.service_with_defaults.container.environment, try(coalesce(try(var.override.container.environment, null), []), []))
      secrets      = local.service_with_defaults.container.secrets
      mount_points = local.service_with_defaults.container.mount_points
      health_check = local.service_with_defaults.container.health_check
    }

    auto_scaling          = try(coalesce(try(var.override.auto_scaling.enabled, null), local.service_with_defaults.auto_scaling), local.service_with_defaults.auto_scaling)
    min_capacity          = try(coalesce(try(var.override.auto_scaling.min_capacity, null), local.service_with_defaults.min_capacity), local.service_with_defaults.min_capacity)
    max_capacity          = try(coalesce(try(var.override.auto_scaling.max_capacity, null), local.service_with_defaults.max_capacity), local.service_with_defaults.max_capacity)
    scaling_cpu_threshold = try(coalesce(try(var.override.auto_scaling.cpu_threshold, null), local.service_with_defaults.scaling_cpu_threshold), local.service_with_defaults.scaling_cpu_threshold)

    desired_count = coalesce(try(var.override.desired_count, null), local.service_with_defaults.desired_count)

    volumes = local.service_with_defaults.volumes

    lb_listener_rule = local.service_with_defaults.lb_listener_rule

    is_scheduled_task   = local.service_with_defaults.is_scheduled_task
    schedule_expression = local.service_with_defaults.schedule_expression

    policy = local.service_with_defaults.policy
  }
}
