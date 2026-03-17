locals {
  project_name = "ecs-sandbox"
}

variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be one of: staging, production"
  }
}

variable "aws_config" {
  description = "Configuration for AWS infrastructure"
  type = object({
    aws_region = string
    vpc_cidr   = string

    enable_s3_archival = optional(bool, false)

    service_configurations = optional(map(object({
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
    })))

    tags = optional(map(string), {})
  })
  default = null
}
