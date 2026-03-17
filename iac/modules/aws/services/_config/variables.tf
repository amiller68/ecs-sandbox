variable "name" {
  description = "Name of the service"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "service" {
  description = "Base service configuration from each services respective module"
  type = object({
    container = object({
      cpu    = optional(number)
      memory = optional(number)
      environment = optional(list(object({
        name  = string
        value = string
      })))
      secrets = optional(list(object({
        name      = string
        valueFrom = string
      })))
      mount_points = optional(list(object({
        sourceVolume  = string
        containerPath = string
        readOnly      = optional(bool)
      })))
    })

    desired_count = optional(number)
    auto_scaling = optional(object({
      enabled       = bool
      min_capacity  = number
      max_capacity  = number
      cpu_threshold = number
    }))

    # Services without load balancers set this to null
    lb_listener_rule = optional(object({
      path_pattern = list(string)
    }))

    volumes = optional(list(object({
      name = string
      efs = optional(object({
        creation_token   = string
        encrypted        = bool
        performance_mode = string
        throughput_mode  = string
        owner_uid        = string
        owner_gid        = string
        permissions      = string
        root_directory   = string
      }))
    })))

    # Scheduled task support
    is_scheduled_task   = optional(bool)
    schedule_expression = optional(string)

    policy = optional(object({
      Version = string
      Statement = list(object({
        Effect   = string
        Action   = list(string)
        Resource = list(string)
      }))
    }))
  })
}

variable "override" {
  description = "Environment-specific overrides"
  type = object({
    container = optional(object({
      cpu    = optional(number)
      memory = optional(number)
      environment = optional(list(object({
        name  = string
        value = string
      })))
    }))

    desired_count = optional(number)
    auto_scaling = optional(object({
      enabled       = optional(bool)
      min_capacity  = optional(number)
      max_capacity  = optional(number)
      cpu_threshold = optional(number)
    }))
  })
  default = null
}
