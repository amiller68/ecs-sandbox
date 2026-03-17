variable "environment" {
  description = "Environment name"
  type        = string
}

# Optional per-environment service configuration overrides
variable "service_configurations" {
  description = "Optional per-environment service configuration overrides"
  type = map(object({
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
  }))
  default = {}
}

# S3 bucket for workspace archival (passed to ecs-sandbox service)
variable "s3_workspace_bucket_arn" {
  description = "ARN of the S3 bucket for workspace archival"
  type        = string
  default     = ""
}

variable "s3_workspace_bucket_name" {
  description = "Name of the S3 bucket for workspace archival"
  type        = string
  default     = ""
}
